"""
╔══════════════════════════════════════════════════════════════╗
║           SOLIS AI — FACE LOCK SYSTEM  v1.1                ║
╠══════════════════════════════════════════════════════════════╣
║  INSTALL DEPENDENCIES BEFORE RUNNING:                       ║
║    pip install opencv-python numpy mediapipe customtkinter  ║
║    pip install cmake dlib face_recognition                  ║
╚══════════════════════════════════════════════════════════════╝
"""

# ──────────────────────────────────────────────────────────────
# SECTION 0 — AUTO DEPENDENCY CHECK
# ──────────────────────────────────────────────────────────────
import subprocess, sys, importlib

REQUIRED = {
    "cv2":              "opencv-python",
    "numpy":            "numpy",
    "mediapipe":        "mediapipe",
    "customtkinter":    "customtkinter",
    "face_recognition": "face_recognition",
}

def check_deps():
    missing = [pip for mod, pip in REQUIRED.items()
               if importlib.util.find_spec(mod) is None]
    if missing:
        print("Missing packages:", missing)
        ans = input("Install now? [y/N]: ").strip().lower()
        if ans == "y":
            for p in missing:
                subprocess.check_call([sys.executable, "-m", "pip", "install", p])
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        else:
            sys.exit(1)

check_deps()

# ──────────────────────────────────────────────────────────────
# SECTION 1 — IMPORTS
# ──────────────────────────────────────────────────────────────
import os, json, math, time, hashlib, threading, datetime
import tkinter as tk
import cv2
import numpy as np
import face_recognition
import mediapipe as mp
import customtkinter as ctk

# ──────────────────────────────────────────────────────────────
# SECTION 2 — CONSTANTS
# ──────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
FACE_FILE    = os.path.join(SCRIPT_DIR, "face_data.json")
LOGS_FILE    = os.path.join(SCRIPT_DIR, "logs.json")

ADMIN_HASH   = hashlib.sha256(b"SolisAdmin2026").hexdigest()
TOLERANCE    = 0.48          # Face match distance threshold
REG_SAMPLES  = 12            # Frames to average for registration encoding

EAR_THRESH   = 0.22          # Eye aspect ratio below = closed
BLINK_NEED   = 2             # Blinks required for liveness
HEAD_THRESH  = 14            # Pixel drift for head move
HEAD_NEED    = 2             # Direction changes required

# Colour palette
BG      = "#050c14"
SURFACE = "#0c1824"
BORDER  = "#1a2d45"
ACCENT  = "#00c8f0"
GREEN   = "#00e87a"
RED     = "#ff2d55"
AMBER   = "#ffaa00"
DIM     = "#3a5570"
WHITE   = "#ddeeff"

# ──────────────────────────────────────────────────────────────
# SECTION 3 — LOGGING
# ──────────────────────────────────────────────────────────────
def append_log(success: bool, reason: str):
    logs = []
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE) as f:
                logs = json.load(f)
        except Exception:
            logs = []
    now = datetime.datetime.now()
    logs.append({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "success": success,
        "reason": reason,
    })
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=2)

def last_log_text() -> str:
    if not os.path.exists(LOGS_FILE):
        return ""
    try:
        with open(LOGS_FILE) as f:
            logs = json.load(f)
        if logs:
            e = logs[-1]
            icon = "✓" if e["success"] else "✗"
            return f"Last: {e['date']} {e['time']}  {icon}  {e['reason']}"
    except Exception:
        pass
    return ""

# ──────────────────────────────────────────────────────────────
# SECTION 4 — FACE DATA STORAGE
# ──────────────────────────────────────────────────────────────
def has_face_data() -> bool:
    return os.path.exists(FACE_FILE)

def load_face_enc() -> np.ndarray | None:
    try:
        with open(FACE_FILE) as f:
            d = json.load(f)
        return np.array(d["encoding"])
    except Exception as e:
        print(f"[FACE LOAD ERROR] {e}")
        return None

def save_face_enc(enc: np.ndarray):
    if has_face_data():
        raise RuntimeError("face_data.json already exists.")
    now = datetime.datetime.now()
    with open(FACE_FILE, "w") as f:
        json.dump({
            "encoding":   enc.tolist(),
            "registered": now.isoformat(),
        }, f, indent=2)

def delete_face_data():
    if os.path.exists(FACE_FILE):
        os.remove(FACE_FILE)

# ──────────────────────────────────────────────────────────────
# SECTION 5 — LIVENESS DETECTOR (MediaPipe Face Mesh)
# ──────────────────────────────────────────────────────────────
class Liveness:
    # Eye landmark indices (MediaPipe)
    L_TOP, L_BOT, L_L, L_R = 159, 145, 33, 133
    R_TOP, R_BOT, R_L, R_R = 386, 374, 362, 263
    NOSE = 4

    def __init__(self):
        self.mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.reset()

    def reset(self):
        self.blinks      = 0
        self.blink_frames = 0
        self.head_moves  = 0
        self.last_dir    = None
        self.prev_nose_x = None
        self.passed      = False

    def _ear(self, lm, t, b, l, r, w, h):
        vert = abs(lm[t].y - lm[b].y) * h
        horz = abs(lm[l].x - lm[r].x) * w
        return vert / horz if horz > 0 else 0.0

    def process(self, rgb: np.ndarray) -> dict:
        """
        Returns dict: passed, blinks, head_moves, face_found, hint
        rgb must be HxWx3 uint8 RGB.
        """
        h, w = rgb.shape[:2]
        res  = self.mesh.process(rgb)

        out = dict(passed=self.passed, blinks=self.blinks,
                   head_moves=self.head_moves, face_found=False,
                   hint="No face detected")

        if not res.multi_face_landmarks:
            return out

        lm = res.multi_face_landmarks[0].landmark
        out["face_found"] = True

        # — Blink detection via EAR —
        ear = (self._ear(lm, self.L_TOP, self.L_BOT, self.L_L, self.L_R, w, h)
             + self._ear(lm, self.R_TOP, self.R_BOT, self.R_L, self.R_R, w, h)) / 2

        if ear < EAR_THRESH:
            self.blink_frames += 1
        else:
            if self.blink_frames >= 1:
                self.blinks += 1
            self.blink_frames = 0

        # — Head movement via nose X drift —
        nx = lm[self.NOSE].x * w
        if self.prev_nose_x is not None:
            dx = nx - self.prev_nose_x
            if abs(dx) > HEAD_THRESH:
                d = "R" if dx > 0 else "L"
                if d != self.last_dir:
                    self.head_moves += 1
                    self.last_dir = d
        self.prev_nose_x = nx

        out["blinks"]     = self.blinks
        out["head_moves"] = self.head_moves

        # — Verdict —
        if self.blinks >= BLINK_NEED and self.head_moves >= HEAD_NEED:
            self.passed = True
            out["passed"] = True
            out["hint"]   = "Liveness confirmed ✓"
        else:
            parts = []
            if self.blinks < BLINK_NEED:
                parts.append(f"Blink {BLINK_NEED - self.blinks} more time(s)")
            if self.head_moves < HEAD_NEED:
                parts.append(f"Turn head {HEAD_NEED - self.head_moves} more time(s)")
            out["hint"] = "  •  ".join(parts)

        return out

    def close(self):
        self.mesh.close()

# ──────────────────────────────────────────────────────────────
# SECTION 6 — FRAME → TKINTER PHOTO  (fast PPM method)
# ──────────────────────────────────────────────────────────────
def frame_to_photo(rgb: np.ndarray) -> tk.PhotoImage:
    """Convert a uint8 RGB numpy array to tk.PhotoImage via PPM bytes."""
    h, w = rgb.shape[:2]
    header = f"P6\n{w} {h}\n255\n".encode()
    photo  = tk.PhotoImage(width=w, height=h)
    photo.put(header + rgb.tobytes(), format="PPM")
    return photo

# ──────────────────────────────────────────────────────────────
# SECTION 7 — MAIN APPLICATION
# ──────────────────────────────────────────────────────────────
class SolisApp(ctk.CTk):
    CAM_W  = 480    # Camera preview width  (pixels)
    CAM_H  = 360    # Camera preview height (pixels)
    WIN_W  = 800    # Total window width
    WIN_H  = 560    # Total window height

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # — Window setup (NOT fullscreen) —
        self.title("SOLIS AI — Face Lock")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        # Centre on screen
        self.after(0, self._centre_window)

        # — State —
        self.mode       = "INIT"
        self.cap        = None
        self.cam_active = False
        self.frame_lock = threading.Lock()
        self._raw_frame = None      # Latest BGR frame from camera thread
        self._photo_ref = None      # Keeps tk.PhotoImage alive

        self.liveness   = Liveness()
        self.stored_enc = None
        self.reg_buf    = []        # Encoding samples during registration
        self._glow_t    = 0

        # — Build UI —
        self._build_ui()
        self._tick_clock()
        self._tick_glow()

        # — Decide mode —
        if has_face_data():
            self.stored_enc = load_face_enc()
            if self.stored_enc is None:
                self._status("face_data.json is corrupt — reset required.", RED)
            else:
                self._start_auth()
        else:
            self._start_reg()

        self.protocol("WM_DELETE_WINDOW", self._quit)

    # ── CENTRING ──────────────────────────────────────────────
    def _centre_window(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.WIN_W) // 2
        y  = (sh - self.WIN_H) // 2
        self.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+{y}")

    # ── UI CONSTRUCTION ───────────────────────────────────────
    def _build_ui(self):
        # Root grid: header / body / footer
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── HEADER ─────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=SURFACE, height=54,
                            corner_radius=0,
                            border_width=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        self.title_lbl = ctk.CTkLabel(
            hdr, text="⬡  SOLIS AI",
            font=ctk.CTkFont("Courier New", 22, "bold"),
            text_color=ACCENT)
        self.title_lbl.grid(row=0, column=0, padx=18, pady=14)

        self.clock_lbl = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont("Courier New", 11),
            text_color=DIM)
        self.clock_lbl.grid(row=0, column=2, padx=18)

        # Mode badge (centre of header)
        self.badge = ctk.CTkLabel(
            hdr, text="INITIALIZING",
            font=ctk.CTkFont("Courier New", 10, "bold"),
            text_color=BG, fg_color=AMBER,
            corner_radius=4, width=130, height=22)
        self.badge.grid(row=0, column=1)

        # ── BODY (camera left | info right) ───────────────────
        body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Camera panel
        cam_frame = ctk.CTkFrame(body, fg_color=SURFACE,
                                  corner_radius=10,
                                  border_width=1, border_color=BORDER)
        cam_frame.grid(row=0, column=0, padx=(14,7), pady=14, sticky="nsew")

        self.canvas = tk.Canvas(cam_frame,
                                width=self.CAM_W, height=self.CAM_H,
                                bg=BG, highlightthickness=0)
        self.canvas.pack(padx=8, pady=8)
        self._placeholder()

        # Info panel
        info = ctk.CTkFrame(body, fg_color=SURFACE,
                             corner_radius=10,
                             border_width=1, border_color=BORDER)
        info.grid(row=0, column=1, padx=(7,14), pady=14, sticky="nsew")
        info.grid_columnconfigure(0, weight=1)

        # Status heading
        self.head_lbl = ctk.CTkLabel(
            info, text="Starting...",
            font=ctk.CTkFont("Courier New", 17, "bold"),
            text_color=WHITE, wraplength=240, justify="left")
        self.head_lbl.grid(row=0, column=0, padx=18, pady=(20,4), sticky="w")

        # Detail text
        self.detail_lbl = ctk.CTkLabel(
            info, text="",
            font=ctk.CTkFont("Courier New", 11),
            text_color=DIM, wraplength=240, justify="left")
        self.detail_lbl.grid(row=1, column=0, padx=18, pady=(0,12), sticky="w")

        # Divider
        ctk.CTkFrame(info, height=1, fg_color=BORDER).grid(
            row=2, column=0, sticky="ew", padx=14)

        # Liveness section label
        ctk.CTkLabel(info, text="LIVENESS CHECK",
                     font=ctk.CTkFont("Courier New", 9, "bold"),
                     text_color=DIM).grid(
            row=3, column=0, padx=18, pady=(12,4), sticky="w")

        # Blink row
        brow = ctk.CTkFrame(info, fg_color="transparent")
        brow.grid(row=4, column=0, padx=18, pady=2, sticky="ew")
        brow.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(brow, text="Blink",
                     font=ctk.CTkFont("Courier New", 12),
                     text_color=DIM).grid(row=0, column=0, sticky="w")
        self.blink_lbl = ctk.CTkLabel(brow, text=f"0/{BLINK_NEED}",
                                       font=ctk.CTkFont("Courier New", 12, "bold"),
                                       text_color=DIM)
        self.blink_lbl.grid(row=0, column=2, sticky="e")

        # Head row
        hrow = ctk.CTkFrame(info, fg_color="transparent")
        hrow.grid(row=5, column=0, padx=18, pady=2, sticky="ew")
        hrow.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hrow, text="Head turn",
                     font=ctk.CTkFont("Courier New", 12),
                     text_color=DIM).grid(row=0, column=0, sticky="w")
        self.head_lbl2 = ctk.CTkLabel(hrow, text=f"0/{HEAD_NEED}",
                                       font=ctk.CTkFont("Courier New", 12, "bold"),
                                       text_color=DIM)
        self.head_lbl2.grid(row=0, column=2, sticky="e")

        # Progress bar
        self.prog = ctk.CTkProgressBar(info, width=220, height=5,
                                        fg_color=BORDER,
                                        progress_color=ACCENT)
        self.prog.set(0)
        self.prog.grid(row=6, column=0, padx=18, pady=(6,14), sticky="w")

        # Divider
        ctk.CTkFrame(info, height=1, fg_color=BORDER).grid(
            row=7, column=0, sticky="ew", padx=14)

        # Buttons
        self.admin_btn = ctk.CTkButton(
            info, text="⚙  Admin Reset", height=30,
            font=ctk.CTkFont("Courier New", 11),
            fg_color="transparent", border_width=1, border_color=BORDER,
            text_color=DIM, hover_color=BG,
            command=self._admin_dialog)
        self.admin_btn.grid(row=8, column=0, padx=18, pady=(12,4), sticky="ew")

        ctk.CTkButton(
            info, text="✕  Exit", height=30,
            font=ctk.CTkFont("Courier New", 11),
            fg_color="transparent", border_width=1, border_color=BORDER,
            text_color=RED, hover_color=BG,
            command=self._quit).grid(
            row=9, column=0, padx=18, pady=(0,16), sticky="ew")

        # ── FOOTER ─────────────────────────────────────────────
        ftr = ctk.CTkFrame(self, fg_color=SURFACE, height=28,
                            corner_radius=0)
        ftr.grid(row=2, column=0, sticky="ew")
        ftr.grid_propagate(False)
        self.log_lbl = ctk.CTkLabel(ftr, text="",
                                     font=ctk.CTkFont("Courier New", 10),
                                     text_color=DIM)
        self.log_lbl.pack(side="left", padx=14)

    # ── PLACEHOLDER ────────────────────────────────────────────
    def _placeholder(self):
        self.canvas.delete("ph")
        self.canvas.create_text(
            self.CAM_W // 2, self.CAM_H // 2,
            text="[ CAMERA OFFLINE ]",
            fill=DIM, font=("Courier New", 12), tags="ph")

    # ── CLOCK ─────────────────────────────────────────────────
    def _tick_clock(self):
        self.clock_lbl.configure(
            text=datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ── GLOW ANIMATION ────────────────────────────────────────
    def _tick_glow(self):
        self._glow_t = (self._glow_t + 3) % 360
        t = (math.sin(math.radians(self._glow_t)) + 1) / 2
        r = int(t * 60)
        g = int(180 + t * 75)
        b = int(220 + t * 35)
        try:
            self.title_lbl.configure(
                text_color=f"#{min(r,255):02x}{min(g,255):02x}{min(b,255):02x}")
        except Exception:
            pass
        self.after(45, self._tick_glow)

    # ── STATUS HELPERS ─────────────────────────────────────────
    def _status(self, heading, color=WHITE, detail="",
                badge_text=None, badge_color=None):
        self.head_lbl.configure(text=heading, text_color=color)
        self.detail_lbl.configure(text=detail)
        if badge_text:
            self.badge.configure(text=badge_text,
                                  fg_color=badge_color or AMBER)
        self.log_lbl.configure(text=last_log_text())

    def _liveness_ui(self, blinks, head_moves):
        b_ok = blinks    >= BLINK_NEED
        h_ok = head_moves >= HEAD_NEED
        self.blink_lbl.configure(
            text=f"{min(blinks, BLINK_NEED)}/{BLINK_NEED}",
            text_color=GREEN if b_ok else WHITE)
        self.head_lbl2.configure(
            text=f"{min(head_moves, HEAD_NEED)}/{HEAD_NEED}",
            text_color=GREEN if h_ok else WHITE)
        p = min((blinks / BLINK_NEED + head_moves / HEAD_NEED) / 2, 1.0)
        self.prog.set(p)
        self.prog.configure(progress_color=GREEN if p >= 1.0 else ACCENT)

    # ── CAMERA ────────────────────────────────────────────────
    def _cam_start(self):
        if self.cam_active:
            return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._status("Camera not found.", RED,
                         detail="Connect a webcam and restart.")
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cam_active = True
        threading.Thread(target=self._cam_loop, daemon=True).start()

    def _cam_stop(self):
        self.cam_active = False
        time.sleep(0.12)
        if self.cap:
            self.cap.release()
            self.cap = None

    def _cam_loop(self):
        """Background thread: continuously reads BGR frames."""
        while self.cam_active:
            if not self.cap or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)   # mirror
                with self.frame_lock:
                    self._raw_frame = frame

    def _get_bgr(self):
        with self.frame_lock:
            return (self._raw_frame.copy()
                    if self._raw_frame is not None else None)

    # ── FRAME DISPLAY ─────────────────────────────────────────
    def _show_frame(self, bgr: np.ndarray,
                    face_locs=None, box_color=(0, 200, 240), lbl=""):
        """
        Resize BGR → fit canvas, draw boxes, convert to PPM PhotoImage.
        face_locs: list of (top, right, bottom, left) in original-frame coords
        box_color: BGR tuple
        """
        if bgr is None:
            return

        # Resize to fit canvas
        fh, fw = bgr.shape[:2]
        scale  = min(self.CAM_W / fw, self.CAM_H / fh)
        nw, nh = int(fw * scale), int(fh * scale)
        disp   = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)

        # Draw face bounding boxes (corner-bracket style)
        if face_locs:
            for (top, right, bottom, left) in face_locs:
                t = int(top    * scale)
                r = int(right  * scale)
                b = int(bottom * scale)
                l = int(left   * scale)
                c, th = box_color, 2
                k = 16
                cv2.line(disp, (l,t), (l+k,t), c, th)
                cv2.line(disp, (l,t), (l,t+k), c, th)
                cv2.line(disp, (r,t), (r-k,t), c, th)
                cv2.line(disp, (r,t), (r,t+k), c, th)
                cv2.line(disp, (l,b), (l+k,b), c, th)
                cv2.line(disp, (l,b), (l,b-k), c, th)
                cv2.line(disp, (r,b), (r-k,b), c, th)
                cv2.line(disp, (r,b), (r,b-k), c, th)
                if lbl:
                    cv2.putText(disp, lbl, (l, t - 8),
                                cv2.FONT_HERSHEY_DUPLEX, 0.48,
                                c, 1, cv2.LINE_AA)

        # Subtle scanline effect
        disp[::5] = (disp[::5] * 0.72).astype(np.uint8)

        # HUD timestamp
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        cv2.putText(disp, f"SOLIS  {ts}",
                    (6, nh - 8), cv2.FONT_HERSHEY_DUPLEX,
                    0.38, box_color, 1, cv2.LINE_AA)

        # BGR → RGB then PPM PhotoImage
        rgb   = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        photo = frame_to_photo(rgb)

        # Centre on canvas
        ox = (self.CAM_W - nw) // 2
        oy = (self.CAM_H - nh) // 2
        self.canvas.delete("feed")
        self.canvas.create_image(ox, oy, anchor="nw",
                                  image=photo, tags="feed")
        self._photo_ref = photo   # prevent GC

    # ─────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────
    def _start_reg(self):
        self.mode = "REG"
        self.reg_buf.clear()
        self.liveness.reset()
        self._status("Face Registration",
                     AMBER,
                     detail="Look at the camera.\nStay still while sampling...",
                     badge_text="FIRST LAUNCH",
                     badge_color=AMBER)
        self._cam_start()
        self.after(400, self._reg_tick)

    def _reg_tick(self):
        if self.mode != "REG":
            return

        bgr = self._get_bgr()
        if bgr is None:
            self.after(80, self._reg_tick)
            return

        # ── CRITICAL FIX: convert BGR → uint8 RGB before face_recognition ──
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.uint8)

        face_locs = face_recognition.face_locations(rgb, model="hog")

        total = REG_SAMPLES
        count = len(self.reg_buf)

        if face_locs:
            encs = face_recognition.face_encodings(rgb, face_locs)
            if encs:
                self.reg_buf.append(encs[0])
            self._show_frame(bgr, face_locs,
                             box_color=(200, 130, 0),
                             lbl=f"{count}/{total}")
            self._status("Capturing face...", AMBER,
                         detail=f"Samples: {count} / {total}\nHold still...",
                         badge_text="REGISTERING", badge_color=AMBER)
            p = count / total
            self.prog.set(min(p, 1.0))
        else:
            self._show_frame(bgr)
            self._status("No face detected", RED,
                         detail="Move closer to the camera.",
                         badge_text="REGISTERING", badge_color=AMBER)

        if len(self.reg_buf) >= total:
            self._finish_reg()
            return

        self.after(100, self._reg_tick)

    def _finish_reg(self):
        avg = np.mean(self.reg_buf, axis=0)
        try:
            save_face_enc(avg)
        except RuntimeError as e:
            self._status("Save error", RED, detail=str(e))
            return

        append_log(True, "Owner face registered")
        self._cam_stop()
        self.prog.set(1.0)
        self.prog.configure(progress_color=GREEN)
        self._status("Owner Face Registered Successfully",
                     GREEN,
                     detail="Welcome to Solis AI\n\nStarting authentication...",
                     badge_text="REGISTERED", badge_color=GREEN)
        self.after(2500, self._after_reg)

    def _after_reg(self):
        self.stored_enc = load_face_enc()
        self.liveness.reset()
        self._start_auth()

    # ─────────────────────────────────────────────────────────
    # AUTHENTICATION
    # ─────────────────────────────────────────────────────────
    def _start_auth(self):
        self.mode = "AUTH"
        self.liveness.reset()
        self._liveness_ui(0, 0)
        self._status("Authenticating...", ACCENT,
                     detail=f"Blink {BLINK_NEED}x and turn head to verify liveness.",
                     badge_text="LOCKED", badge_color=RED)
        self._cam_start()
        self.after(400, self._auth_tick)

    def _auth_tick(self):
        if self.mode != "AUTH":
            return

        bgr = self._get_bgr()
        if bgr is None:
            self.after(80, self._auth_tick)
            return

        # ── CRITICAL FIX: ensure uint8 RGB for face_recognition ──
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.uint8)

        # Liveness
        lv = self.liveness.process(rgb)
        self._liveness_ui(lv["blinks"], lv["head_moves"])

        face_locs = face_recognition.face_locations(rgb, model="hog")

        if not face_locs:
            self._show_frame(bgr)
            self._status("No face detected", AMBER,
                         detail="Position your face in the frame.",
                         badge_text="LOCKED", badge_color=RED)
            self.after(80, self._auth_tick)
            return

        if not lv["passed"]:
            self._show_frame(bgr, face_locs,
                             box_color=(200, 160, 0), lbl="Verifying...")
            self._status("Liveness Check", AMBER,
                         detail=lv["hint"],
                         badge_text="LOCKED", badge_color=RED)
            self.after(80, self._auth_tick)
            return

        # Liveness passed → compare face
        encs = face_recognition.face_encodings(rgb, face_locs)
        if not encs:
            self.after(80, self._auth_tick)
            return

        dist  = face_recognition.face_distance([self.stored_enc], encs[0])[0]
        match = dist <= TOLERANCE

        if match:
            self._show_frame(bgr, face_locs,
                             box_color=(0, 232, 100), lbl="OWNER")
            self._auth_ok(dist)
        else:
            self._show_frame(bgr, face_locs,
                             box_color=(50, 45, 255), lbl="UNKNOWN")
            self._auth_fail(dist)

    def _auth_ok(self, dist):
        self.mode = "UNLOCKED"
        append_log(True, f"Auth success (dist={dist:.3f})")
        self._cam_stop()
        conf = int((1.0 - dist) * 100)
        self._status("Welcome to Solis AI", GREEN,
                     detail=f"Identity confirmed.\nConfidence: {conf}%",
                     badge_text="UNLOCKED", badge_color=GREEN)
        self.prog.set(1.0)
        self.prog.configure(progress_color=GREEN)

    def _auth_fail(self, dist):
        self.mode = "FAIL"
        append_log(False, f"Auth failed (dist={dist:.3f})")
        self._cam_stop()
        self._status("Access Denied", RED,
                     detail="Face not recognised.\nThis attempt has been logged.",
                     badge_text="DENIED", badge_color=RED)
        self.after(3500, self._retry)

    def _retry(self):
        self.liveness.reset()
        self._start_auth()

    # ─────────────────────────────────────────────────────────
    # ADMIN RESET
    # ─────────────────────────────────────────────────────────
    def _admin_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Admin Reset")
        dlg.geometry("360x200")
        dlg.configure(fg_color=SURFACE)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.lift()

        ctk.CTkLabel(dlg, text="ADMIN RESET",
                     font=ctk.CTkFont("Courier New", 16, "bold"),
                     text_color=RED).pack(pady=(18,4))

        ctk.CTkLabel(dlg, text="Enter admin password:",
                     font=ctk.CTkFont("Courier New", 11),
                     text_color=DIM).pack(pady=(0,8))

        pw = ctk.CTkEntry(dlg, show="•", width=240, height=34,
                          font=ctk.CTkFont("Courier New", 13),
                          fg_color=BG, border_color=BORDER, text_color=WHITE)
        pw.pack()
        pw.focus()

        err = ctk.CTkLabel(dlg, text="",
                           font=ctk.CTkFont("Courier New", 10),
                           text_color=RED)
        err.pack(pady=4)

        def attempt():
            entered_hash = hashlib.sha256(pw.get().encode()).hexdigest()
            if entered_hash == ADMIN_HASH:
                delete_face_data()
                append_log(False, "Admin reset — face data deleted")
                dlg.destroy()
                self._cam_stop()
                self.stored_enc = None
                self.liveness.reset()
                self.prog.set(0)
                self.prog.configure(progress_color=ACCENT)
                self._start_reg()
            else:
                append_log(False, "Admin reset — wrong password")
                err.configure(text="✗  Wrong password. Attempt logged.")
                pw.delete(0, "end")

        pw.bind("<Return>", lambda e: attempt())

        bf = ctk.CTkFrame(dlg, fg_color="transparent")
        bf.pack(pady=6)
        ctk.CTkButton(bf, text="Reset", width=100, height=30,
                      fg_color=RED, hover_color="#cc0022",
                      font=ctk.CTkFont("Courier New", 12, "bold"),
                      command=attempt).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="Cancel", width=100, height=30,
                      fg_color="transparent", border_width=1,
                      border_color=BORDER, text_color=DIM,
                      font=ctk.CTkFont("Courier New", 12),
                      command=dlg.destroy).pack(side="left", padx=6)

    # ─────────────────────────────────────────────────────────
    # EXIT
    # ─────────────────────────────────────────────────────────
    def _quit(self):
        self._cam_stop()
        try:
            self.liveness.close()
        except Exception:
            pass
        self.destroy()


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═" * 56)
    print("  ⬡  SOLIS AI  FACE LOCK  v1.1")
    print("═" * 56)
    print(f"  Face file : {FACE_FILE}")
    print(f"  Log  file : {LOGS_FILE}")
    print(f"  Mode      : {'AUTH' if has_face_data() else 'FIRST LAUNCH'}")
    print("═" * 56)
    app = SolisApp()
    app.mainloop()