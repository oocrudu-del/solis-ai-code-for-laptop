"""
✋ Hand Gesture Mouse Controller v2.1
======================================
GESTURES:
  🖐 Open Palm          → Mouse MOVE
  🤏 Index+Thumb PINCH  → LEFT CLICK  (touch gareko bela ek palta)
  🤞 Middle+Thumb PINCH → RIGHT CLICK (touch gareko bela ek palta)
  ✌  2 aula (index+middle up, no pinch) → SCROLL (haath mathi/tala)
  ✊ Fist               → DRAG & DROP

PINCH logic:
  - Fingers aaucha (distance kam huncha) → click fire (ONCE)
  - Fingers TARkai aaucha = click, HOLD garera = click hudaina
  - Pheri TAaDDa garera aaucha = next click ready

QUIT: 'Q' thichne  |  Mouse lai top-left corner lanu
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
from collections import deque

# ── Config ────────────────────────────────────────────────────────────────────
CAM_INDEX         = 0
SMOOTH_FRAMES     = 7
SCROLL_SENS       = 700
ACTIVE_MARGIN     = 0.12
FLIP              = True

# Pinch thresholds (normalized 0-1 distance)
PINCH_CLOSE       = 0.045   # yo bhanda kam = pinched (click fire)
PINCH_OPEN        = 0.075   # yo bhanda badi = open (ready for next click)

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0
SW, SH = pyautogui.size()

mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles  = mp.solutions.drawing_styles

TIPS = [4, 8, 12, 16, 20]
PIPS = [3, 6, 10, 14, 18]
MCPS = [2, 5,  9, 13, 17]

# ── Gesture labels ────────────────────────────────────────────────────────────
class G:
    NONE   = "None"
    MOVE   = "Open Palm - Moving"
    LCLICK = "Left Click"
    RCLICK = "Right Click"
    SCROLL = "Scrolling"
    DRAG   = "Drag & Drop"

COLORS = {
    G.NONE:   (80,  80,  80),
    G.MOVE:   (50,  220, 120),
    G.LCLICK: (50,  140, 255),
    G.RCLICK: (0,   210, 210),
    G.SCROLL: (200, 80,  220),
    G.DRAG:   (220, 100, 30),
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def dist2d(hand, a, b):
    pa = hand.landmark[a]
    pb = hand.landmark[b]
    return np.hypot(pa.x - pb.x, pa.y - pb.y)

def fingers_up(hand):
    f = []
    # Thumb
    f.append(hand.landmark[4].x < hand.landmark[3].x)
    for tip, pip in zip(TIPS[1:], PIPS[1:]):
        f.append(hand.landmark[tip].y < hand.landmark[pip].y)
    return f  # [thumb, index, middle, ring, pinky]

def palm_center(hand):
    pts = [0] + MCPS
    xs = [hand.landmark[i].x for i in pts]
    ys = [hand.landmark[i].y for i in pts]
    return float(np.mean(xs)), float(np.mean(ys))

def map_screen(nx, ny):
    lo, hi = ACTIVE_MARGIN, 1.0 - ACTIVE_MARGIN
    nx = max(lo, min(hi, nx))
    ny = max(lo, min(hi, ny))
    sx = int((nx - lo) / (hi - lo) * SW)
    sy = int((ny - lo) / (hi - lo) * SH)
    return sx, sy

# ── Smoother ──────────────────────────────────────────────────────────────────
class Smoother:
    def __init__(self, n):
        self.qx = deque([0.0]*n, maxlen=n)
        self.qy = deque([0.0]*n, maxlen=n)
    def update(self, x, y):
        self.qx.append(x); self.qy.append(y)
        return int(np.mean(self.qx)), int(np.mean(self.qy))

# ── Pinch State Machine ───────────────────────────────────────────────────────
# Har ek click type ko lagi alag state:
# "open"   = fingers TAaDDa xa, click fire garna ready
# "closed" = fingers jodiyeko xa (click already fired)
class PinchTracker:
    def __init__(self):
        self.state = "open"   # "open" | "closed"

    def update(self, distance):
        """
        Returns True only on the MOMENT fingers touch (open→closed transition).
        Hold garera rakhe pani ek palta matra True aaucha.
        """
        fired = False
        if self.state == "open" and distance < PINCH_CLOSE:
            fired = True
            self.state = "closed"
        elif self.state == "closed" and distance > PINCH_OPEN:
            self.state = "open"   # reset: next pinch ko lagi ready
        return fired

# ── Main classify ─────────────────────────────────────────────────────────────
def classify(hand):
    """Return base gesture (pinch check alag garcha)."""
    f = fingers_up(hand)
    thumb, idx, mid, ring, pinky = f
    count = sum(f[1:])

    # Fist
    if count == 0:
        return G.DRAG

    # 2 fingers up (scroll mode) - no pinch check here
    if count == 2 and idx and mid and not ring and not pinky:
        return G.SCROLL

    # Open palm → move
    if count >= 3:
        return G.MOVE

    return G.NONE

# ── HUD ───────────────────────────────────────────────────────────────────────
def draw_hud(frame, gesture, fps, drag_on, scroll_dir,
             l_pinch_d, r_pinch_d, l_ready, r_ready):
    h, w = frame.shape[:2]
    c = COLORS.get(gesture, (200, 200, 200))

    # Top bar background
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 54), (15, 18, 28), -1)
    cv2.addWeighted(ov, 0.78, frame, 0.22, 0, frame)

    cv2.putText(frame, gesture, (12, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.82, c, 2, cv2.LINE_AA)
    cv2.putText(frame, f"FPS {fps:.0f}", (w - 90, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (160, 160, 160), 1, cv2.LINE_AA)

    # Pinch meters (bottom-left area)
    bar_x, bar_y = 10, h - 70
    bar_w = 120

    # Left click pinch bar
    l_pct = max(0.0, min(1.0, 1.0 - (l_pinch_d / PINCH_OPEN)))
    l_col = (50, 255, 100) if l_ready else (50, 140, 255)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 14), (40, 40, 50), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * l_pct), bar_y + 14), l_col, -1)
    cv2.putText(frame, "L-CLICK pinch", (bar_x, bar_y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, l_col, 1, cv2.LINE_AA)

    # Right click pinch bar
    bar_y2 = bar_y + 26
    r_pct = max(0.0, min(1.0, 1.0 - (r_pinch_d / PINCH_OPEN)))
    r_col = (50, 255, 100) if r_ready else (0, 210, 210)
    cv2.rectangle(frame, (bar_x, bar_y2), (bar_x + bar_w, bar_y2 + 14), (40, 40, 50), -1)
    cv2.rectangle(frame, (bar_x, bar_y2), (bar_x + int(bar_w * r_pct), bar_y2 + 14), r_col, -1)
    cv2.putText(frame, "R-CLICK pinch", (bar_x, bar_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, r_col, 1, cv2.LINE_AA)

    # Drag badge
    if drag_on:
        cv2.rectangle(frame, (w - 130, 60), (w - 5, 88), (220, 100, 30), -1)
        cv2.putText(frame, "DRAGGING", (w - 125, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    # Scroll direction
    if scroll_dir == "up":
        cv2.putText(frame, "  SCROLL UP", (w // 2 - 60, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 80, 220), 2, cv2.LINE_AA)
    elif scroll_dir == "down":
        cv2.putText(frame, "  SCROLL DOWN", (w // 2 - 70, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 80, 220), 2, cv2.LINE_AA)

    # Active zone box
    lx = int(ACTIVE_MARGIN * w);  ty = int(ACTIVE_MARGIN * h)
    rx = int((1 - ACTIVE_MARGIN) * w); by_ = int((1 - ACTIVE_MARGIN) * h)
    cv2.rectangle(frame, (lx, ty), (rx, by_), (50, 55, 80), 1)

    # Bottom hint
    cv2.putText(frame, "Palm=Move  Thumb+Index=LClick  Thumb+Middle=RClick  2fingers=Scroll  Fist=Drag",
                (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (110, 115, 135), 1, cv2.LINE_AA)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    smoother    = Smoother(SMOOTH_FRAMES)
    l_pinch     = PinchTracker()   # index + thumb  → left click
    r_pinch     = PinchTracker()   # middle + thumb → right click

    drag_on     = False
    prev_palm_y = None
    scroll_dir  = ""
    prev_time   = time.time()

    print("\n✋  Hand Mouse v2.1  —  Pinch-to-Click Edition")
    print("━" * 50)
    print("  🖐  Open palm (4-5 aula)      → MOVE mouse")
    print("  🤏  Thumb + Index jodne       → LEFT CLICK")
    print("  🤞  Thumb + Middle jodne      → RIGHT CLICK")
    print("  ✌   Index + Middle up          → SCROLL")
    print("  ✊  Fist (sabai banda)         → DRAG & DROP")
    print("━" * 50)
    print("  NOTE: Click = fingers TOUCH gareko moment matra")
    print("        Hold garera rakhe pani ek palta matra click")
    print("        Pheri TAaDDa gara = next click ready")
    print("━" * 50)
    print("  Q key  OR  mouse top-left corner → QUIT\n")

    with mp_hands.Hands(
        model_complexity=0,
        max_num_hands=1,
        min_detection_confidence=0.75,
        min_tracking_confidence=0.70,
    ) as hands:

        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            if FLIP:
                frame = cv2.flip(frame, 1)

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-9)
            prev_time = now

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            res = hands.process(rgb)
            rgb.flags.writeable = True

            gesture    = G.NONE
            scroll_dir = ""

            # Default distances (when no hand)
            l_d = PINCH_OPEN + 0.01
            r_d = PINCH_OPEN + 0.01

            if res.multi_hand_landmarks:
                hand = res.multi_hand_landmarks[0]

                # Draw skeleton
                mp_drawing.draw_landmarks(
                    frame, hand, mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style())

                # Pinch distances (always compute, regardless of gesture)
                l_d = dist2d(hand, 4, 8)   # thumb tip ↔ index tip
                r_d = dist2d(hand, 4, 12)  # thumb tip ↔ middle tip

                # Base gesture
                base = classify(hand)

                # Palm center for cursor
                px, py = palm_center(hand)
                sx, sy = map_screen(px, py)
                sx, sy = smoother.update(sx, sy)

                # ── Pinch click detection (works during MOVE or NONE) ──────
                l_fired = l_pinch.update(l_d)
                r_fired = r_pinch.update(r_d)

                # ── Execute ───────────────────────────────────────────────
                if base == G.DRAG:
                    gesture = G.DRAG
                    pyautogui.moveTo(sx, sy)
                    if not drag_on:
                        pyautogui.mouseDown()
                        drag_on = True
                    prev_palm_y = None

                elif base == G.SCROLL:
                    gesture = G.SCROLL
                    pyautogui.moveTo(sx, sy)
                    if prev_palm_y is not None:
                        delta = py - prev_palm_y
                        if abs(delta) > 0.003:
                            amt = int(-delta * SCROLL_SENS)
                            pyautogui.scroll(amt)
                            scroll_dir = "up" if amt > 0 else "down"
                    prev_palm_y = py
                    if drag_on:
                        pyautogui.mouseUp()
                        drag_on = False

                else:
                    # MOVE or NONE — check pinches
                    pyautogui.moveTo(sx, sy)
                    prev_palm_y = None

                    if l_fired:
                        gesture = G.LCLICK
                        pyautogui.click()
                    elif r_fired:
                        gesture = G.RCLICK
                        pyautogui.rightClick()
                    else:
                        gesture = base if base != G.NONE else G.MOVE

                    if drag_on:
                        pyautogui.mouseUp()
                        drag_on = False

                # Draw cursor dot at palm center
                dot_x = int(px * frame.shape[1])
                dot_y = int(py * frame.shape[0])
                cv2.circle(frame, (dot_x, dot_y), 11, COLORS.get(gesture, (255, 255, 255)), -1)
                cv2.circle(frame, (dot_x, dot_y), 13, (255, 255, 255), 2)

                # Draw pinch lines
                # Left pinch line (thumb→index)
                t  = hand.landmark[4];  idx_lm = hand.landmark[8]
                pt1 = (int(t.x * frame.shape[1]),   int(t.y * frame.shape[0]))
                pt2 = (int(idx_lm.x * frame.shape[1]), int(idx_lm.y * frame.shape[0]))
                l_col_line = (50, 255, 100) if l_d < PINCH_CLOSE else (50, 140, 255)
                cv2.line(frame, pt1, pt2, l_col_line, 2)

                # Right pinch line (thumb→middle)
                mid_lm = hand.landmark[12]
                pt3 = (int(mid_lm.x * frame.shape[1]), int(mid_lm.y * frame.shape[0]))
                r_col_line = (50, 255, 100) if r_d < PINCH_CLOSE else (0, 210, 210)
                cv2.line(frame, pt1, pt3, r_col_line, 2)

            else:
                # No hand detected
                l_pinch.update(PINCH_OPEN + 0.1)
                r_pinch.update(PINCH_OPEN + 0.1)
                if drag_on:
                    pyautogui.mouseUp()
                    drag_on = False
                prev_palm_y = None

            draw_hud(frame, gesture, fps, drag_on, scroll_dir,
                     l_d, r_d,
                     l_pinch.state == "open",
                     r_pinch.state == "open")

            cv2.imshow("Hand Mouse v2.1  |  Q = quit", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if drag_on:
        pyautogui.mouseUp()
    cap.release()
    cv2.destroyAllWindows()
    print("👋 Stopped.")

if __name__ == "__main__":
    main()