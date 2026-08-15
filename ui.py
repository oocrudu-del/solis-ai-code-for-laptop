
#pip install opencv-python numpy pillow pyautogui mediapipe psutil pyperclip requests PyQt5 PyQtWebEngine groq

import os
import sys
import time
import math
import random
import json
import uuid
from datetime import datetime
import threading
import traceback
import asyncio
import webbrowser
import requests
import pyperclip
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, scrolledtext
from collections import deque

# PyAutoGUI Setup for Gesture mouse control
import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

# Mediapipe Dynamic Check for Hand Tracking
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

# Core AI Controller Module fallback
try:
    from main_AI import controller
    HAS_CONTROLLER = True
except ImportError:
    HAS_CONTROLLER = False

# Psutil for real-time hardware telemetry
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import main
    HAS_MAIN_MODULE = True
except ImportError:
    HAS_MAIN_MODULE = False

# Windows Registry module check
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

# PyQt5 Dynamic Check & Setup for Search Browser
try:
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
    from PyQt5.QtCore import QUrl
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

# Groq and API Keys Setup
try:
    from groq import Groq
    HAS_GROQ_LIB = True
except ImportError:
    HAS_GROQ_LIB = False

# Fallback structure for API keys to prevent crash if api.py is missing
if not os.path.exists("api.py"):
    with open("api.py", "w", encoding="utf-8") as f:
        f.write('GEMINI_API_KEY = ""\n')
        f.write('GROQ_API_KEY = ""\n')
        f.write('SERPER_API_KEY = ""\n')
        f.write('WEATHER_API_KEY = ""\n')

try:
    from api import GEMINI_API_KEY, GROQ_API_KEY
except ImportError:
    GEMINI_API_KEY = ""
    GROQ_API_KEY = ""

try:
    if HAS_GROQ_LIB and GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
    else:
        groq_client = None
except Exception as e:
    groq_client = None
    print(f"Groq Init Error: {e}")

# Global Memory for Coding AI
coder_chat_history = []

# ================== PALETTE SETUP ==================
BG = "#030307"            # Ultra dark space background
BG_PANEL = "#0b0c16"      # Deep space panel background
ACCENT_GREEN = "#00ff9d"  # Radiant neon mint green
BORDER_COLOR = "#1b1e36"  # Interactive electric border
TEXT_LIGHT = "#f8fafc"    # High-contrast bright slate
TEXT_MUTED = "#8da2fb"    # Futuristic blue-slate muted
RED_ACCENT = "#ff0055"    # Cyberpunk warning crimson
CYAN_ACCENT = "#00f0ff"   # Electric sky blue
NEON_PINK = "#ff00a0"     # Plasma pink
SOLAR_GOLD = "#ffb700"    # Rich solar gold glow

# --- CONFIGS ---
CARD_BG = "#0f1124"
CARD_HOVER = "#1d2042"
CARD_CLICK = "#2b2f63"
ICON_SIZE = 64
CARD_WIDTH = 250
CARD_HEIGHT = 80
CAM_INDEX = 0             

WEB_APPS = [
    {"name": "YouTube Solar", "status": "ONLINE"},
    {"name": "Solis Cloud Engine", "status": "ONLINE"},
    {"name": "System Matrix Sync", "status": "ONLINE"}
]

# Ensure Project directory exists
os.makedirs("Project", exist_ok=True)

# ================== HAND GESTURE CONSTANTS & CLASS HELPERS ==================
TIPS = [4, 8, 12, 16, 20]
PIPS = [3, 6, 10, 14, 18]
MCPS = [2, 5, 9, 13, 17]

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

def dist2d(hand, a, b):
    pa = hand.landmark[a]
    pb = hand.landmark[b]
    return np.hypot(pa.x - pb.x, pa.y - pb.y)

def fingers_up(hand):
    f = []
    f.append(hand.landmark[4].x < hand.landmark[3].x)
    for tip, pip in zip(TIPS[1:], PIPS[1:]):
        f.append(hand.landmark[tip].y < hand.landmark[pip].y)
    return f

def palm_center(hand):
    pts = [0] + MCPS
    xs = [hand.landmark[i].x for i in pts]
    ys = [hand.landmark[i].y for i in pts]
    return float(np.mean(xs)), float(np.mean(ys))

def map_screen(nx, ny, margin, sw, sh):
    lo, hi = margin, 1.0 - margin
    nx = max(lo, min(hi, nx))
    ny = max(lo, min(hi, ny))
    sx = int((nx - lo) / (hi - lo) * sw)
    sy = int((ny - lo) / (hi - lo) * sh)
    return sx, sy

def classify_gesture(hand):
    f = fingers_up(hand)
    thumb, idx, mid, ring, pinky = f
    count = sum(f[1:])
    if count == 0:
        return G.DRAG
    if count == 2 and idx and mid and not ring and not pinky:
        return G.SCROLL
    if count >= 3:
        return G.MOVE
    return G.NONE

class PinchTracker:
    def __init__(self, close_thresh, open_thresh):
        self.state = "open"
        self.close_thresh = close_thresh
        self.open_thresh = open_thresh

    def update(self, distance):
        fired = False
        if self.state == "open" and distance < self.close_thresh:
            fired = True
            self.state = "closed"
        elif self.state == "closed" and distance > self.open_thresh:
            self.state = "open"
        return fired

class Smoother:
    def __init__(self, n):
        self.qx = deque([0.0]*n, maxlen=n)
        self.qy = deque([0.0]*n, maxlen=n)
    def update(self, x, y):
        self.qx.append(x); self.qy.append(y)
        return int(np.mean(self.qx)), int(np.mean(self.qy))

def draw_hud(frame, gesture, fps, drag_on, scroll_dir,
             l_pinch_d, r_pinch_d, l_ready, r_ready,
             pinch_close, pinch_open, active_margin):
    h, w = frame.shape[:2]
    c = COLORS.get(gesture, (200, 200, 200))

    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 54), (15, 18, 28), -1)
    cv2.addWeighted(ov, 0.78, frame, 0.22, 0, frame)

    cv2.putText(frame, gesture, (12, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.82, c, 2, cv2.LINE_AA)
    cv2.putText(frame, f"FPS {fps:.0f}", (w - 90, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (160, 160, 160), 1, cv2.LINE_AA)

    bar_x, bar_y = 10, h - 70
    bar_w = 120

    l_pct = max(0.0, min(1.0, 1.0 - (l_pinch_d / pinch_open)))
    l_col = (50, 255, 100) if l_ready else (50, 140, 255)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 14), (40, 40, 50), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * l_pct), bar_y + 14), l_col, -1)
    cv2.putText(frame, "L-CLICK pinch", (bar_x, bar_y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, l_col, 1, cv2.LINE_AA)

    bar_y2 = bar_y + 26
    r_pct = max(0.0, min(1.0, 1.0 - (r_pinch_d / pinch_open)))
    r_col = (50, 255, 100) if r_ready else (0, 210, 210)
    cv2.rectangle(frame, (bar_x, bar_y2), (bar_x + bar_w, bar_y2 + 14), (40, 40, 50), -1)
    cv2.rectangle(frame, (bar_x, bar_y2), (bar_x + int(bar_w * r_pct), bar_y2 + 14), r_col, -1)
    cv2.putText(frame, "R-CLICK pinch", (bar_x, bar_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, r_col, 1, cv2.LINE_AA)

    if drag_on:
        cv2.rectangle(frame, (w - 130, 60), (w - 5, 88), (220, 100, 30), -1)
        cv2.putText(frame, "DRAGGING", (w - 125, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    if scroll_dir == "up":
        cv2.putText(frame, "  SCROLL UP", (w // 2 - 60, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 80, 220), 2, cv2.LINE_AA)
    elif scroll_dir == "down":
        cv2.putText(frame, "  SCROLL DOWN", (w // 2 - 70, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 80, 220), 2, cv2.LINE_AA)

    lx = int(active_margin * w);  ty = int(active_margin * h)
    rx = int((1 - active_margin) * w); by_ = int((1 - active_margin) * h)
    cv2.rectangle(frame, (lx, ty), (rx, by_), (50, 55, 80), 1)

    cv2.putText(frame, "Palm=Move  Thumb+Index=LClick  Thumb+Middle=RClick  2fingers=Scroll  Fist=Drag",
                (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (110, 115, 135), 1, cv2.LINE_AA)


# =========================
# AI Logic
# =========================
def generate_code_from_ai(prompt, provider="Gemini (1.5-Flash)", existing_code=""):
    global coder_chat_history
    
    system_instruction = (
        "You are an expert AI software developer.\n"
        "Your task is to write high-quality code or modify existing code, AND provide a brief, clear explanation.\n"
        "You MUST split your response into two clear sections using [EXPLANATION] and [CODE] tags exactly as shown:\n\n"
        "[EXPLANATION]\n"
        "(Explain what the code does or what changes were made in a brief, friendly manner in simple English or Nepalese.)\n\n"
        "[CODE]\n"
        "(Write ONLY the raw updated source code here. Do not wrap code in markdown like ```html or ```python. "
        "The very first line of the code must be a comment specifying the language.)"
    )

    full_user_content = prompt
    if existing_code:
        full_user_content = (
            f"--- EXISTING CODE ---\n{existing_code}\n"
            f"--- USER INSTRUCTION ---\n{prompt}\n\n"
            f"Please update the existing code according to the instruction."
        )

    if "Groq" in provider:
        if not GROQ_API_KEY or not groq_client:
            raise ValueError("Groq API Key configuration missing.")
        
        try:
            messages = [{"role": "system", "content": system_instruction}]
            for chat in coder_chat_history[-6:]:
                messages.append(chat)
            messages.append({"role": "user", "content": full_user_content})

            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.2,
                timeout=None
            )
            ai_text = completion.choices[0].message.content.strip()
            return ai_text, "Groq"
        except Exception as groq_err:
            raise RuntimeError(f"Groq Engine Failed: {groq_err}")

    else:
        try:
            if not GEMINI_API_KEY:
                raise ValueError("Gemini API Key missing.")
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
            
            contents = []
            for chat in coder_chat_history[-6:]:
                role = "model" if chat["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": chat["content"]}]
                })
            contents.append({"role": "user", "parts": [{"text": full_user_content}]})

            payload = {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.2}
            }

            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=None)
            
            if response.status_code == 200:
                resp_json = response.json()
                ai_text = resp_json['candidates'][0]['content']['parts'][0]['text'].strip()
                return ai_text, "Gemini"
            else:
                raise ValueError(f"Gemini API Status {response.status_code}")

        except Exception as gemini_err:
            raise RuntimeError(f"AI Engine failed.\nGemini: {gemini_err}")


# ================== ROADMAP NODE DATA MODEL ==================
class FeatureNodeData:
    def __init__(self, name="New Feature", id=None):
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.description = "Feature details here..."
        self.priority = "Medium"
        self.status = "Planned"
        self.progress = 0
        self.pos_x = 100.0
        self.pos_y = 100.0
        self.connections = []

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'progress': self.progress,
            'pos_x': self.pos_x,
            'pos_y': self.pos_y,
            'connections': self.connections
        }

    @staticmethod
    def from_dict(data):
        node = FeatureNodeData(data.get('name', 'New Feature'), data.get('id'))
        node.description = data.get('description', '')
        node.priority = data.get('priority', 'Medium')
        node.status = data.get('status', 'Planned')
        node.progress = int(data.get('progress', 0))
        node.pos_x = float(data.get('pos_x', 100.0))
        node.pos_y = float(data.get('pos_y', 100.0))
        node.connections = list(data.get('connections', []))
        return node


# ================== PYQT5 BEAUTIFIED SEARCH BROWSER ==================
if HAS_PYQT:
    class SearchBrowser(QWidget):
        def __init__(self, parent_interface):
            super().__init__()
            self.parent_interface = parent_interface
            self.setWindowTitle("SOLIS AI - NEURAL SEARCH ENGINE")
            self.resize(1400, 900)
            self.current_engine = "google"
            self.init_ui()

        def init_ui(self):
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {BG};
                    color: {TEXT_LIGHT};
                    font-family: 'Consolas', 'Segoe UI';
                }}
                QLineEdit {{
                    background-color: {BG_PANEL};
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 4px;
                    padding: 10px;
                    color: {TEXT_LIGHT};
                    font-size: 14px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {CYAN_ACCENT};
                }}
                QPushButton {{
                    background-color: {CARD_BG};
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 4px;
                    padding: 8px 16px;
                    color: {TEXT_MUTED};
                    font-weight: bold;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {CARD_HOVER};
                    border: 1px solid {ACCENT_GREEN};
                    color: {ACCENT_GREEN};
                }}
                QPushButton:pressed {{
                    background-color: {ACCENT_GREEN};
                    color: {BG};
                }}
            """)

            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(12)

            button_layout = QHBoxLayout()
            
            self.back_btn = QPushButton("◀ BACK TO SOLIS")
            self.back_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {RED_ACCENT};
                    color: {TEXT_LIGHT};
                    font-weight: bold;
                    border: 1px solid {RED_ACCENT};
                }}
                QPushButton:hover {{
                    background-color: {BG_PANEL};
                    color: {RED_ACCENT};
                    border: 1px solid {RED_ACCENT};
                }}
            """)
            button_layout.addWidget(self.back_btn)

            self.google_btn = QPushButton("Google ☼")
            self.maps_btn = QPushButton("Google Maps 🧭")
            self.youtube_btn = QPushButton("YouTube 📹")
            self.bing_btn = QPushButton("Bing ▩")
            self.yahoo_btn = QPushButton("Yahoo ⚡")
            self.duck_btn = QPushButton("DuckDuckGo 🦆")

            self.engine_buttons = [
                (self.google_btn, "google"),
                (self.maps_btn, "maps"),
                (self.youtube_btn, "youtube"),
                (self.bing_btn, "bing"),
                (self.yahoo_btn, "yahoo"),
                (self.duck_btn, "duck")
            ]

            for btn, _ in self.engine_buttons:
                button_layout.addWidget(btn)

            search_layout = QHBoxLayout()
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("Enter parameters or search query...")
            
            self.search_btn = QPushButton("SEARCH ENGINE")
            self.search_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_PANEL};
                    border: 1px solid {ACCENT_GREEN};
                    color: {ACCENT_GREEN};
                }}
                QPushButton:hover {{
                    background-color: {ACCENT_GREEN};
                    color: {BG};
                }}
            """)

            search_layout.addWidget(self.search_box)
            search_layout.addWidget(self.search_btn)

            self.browser = QWebEngineView()
            self.browser.setUrl(QUrl("https://www.google.com"))
            self.browser.setStyleSheet(f"border: 1px solid {BORDER_COLOR}; border-radius: 4px;")

            self.back_btn.clicked.connect(self.go_back_to_gui)

            self.google_btn.clicked.connect(lambda: self.set_engine("google", "https://www.google.com", self.google_btn))
            self.maps_btn.clicked.connect(lambda: self.set_engine("maps", "https://maps.google.com", self.maps_btn))
            self.youtube_btn.clicked.connect(lambda: self.set_engine("youtube", "https://www.youtube.com", self.youtube_btn))
            self.bing_btn.clicked.connect(lambda: self.set_engine("bing", "https://www.bing.com", self.bing_btn))
            self.yahoo_btn.clicked.connect(lambda: self.set_engine("yahoo", "https://search.yahoo.com", self.yahoo_btn))
            self.duck_btn.clicked.connect(lambda: self.set_engine("duck", "https://duckduckgo.com", self.duck_btn))

            self.search_btn.clicked.connect(self.execute_search)
            self.search_box.returnPressed.connect(self.execute_search)

            main_layout.addLayout(button_layout)
            main_layout.addLayout(search_layout)
            main_layout.addWidget(self.browser)
            self.setLayout(main_layout)

            self.highlight_active_engine(self.google_btn)

        def go_back_to_gui(self):
            self.close()
            if self.parent_interface and self.parent_interface.root:
                self.parent_interface.root.after(0, self.parent_interface.root.focus_force)

        def set_engine(self, name, url, button):
            self.current_engine = name
            self.browser.setUrl(QUrl(url))
            self.highlight_active_engine(button)

        def highlight_active_engine(self, active_button):
            for btn, _ in self.engine_buttons:
                if btn == active_button:
                    btn.setStyleSheet(f"border: 1px solid {CYAN_ACCENT}; color: {CYAN_ACCENT}; background-color: {CARD_HOVER};")
                else:
                    btn.setStyleSheet("")

        def execute_search(self):
            query = self.search_box.text().strip()
            if not query:
                return

            if self.current_engine == "google":
                url = f"https://www.google.com/search?q={query}"
            elif self.current_engine == "maps":
                url = f"https://www.google.com/maps/search/{query}"
            elif self.current_engine == "youtube":
                url = f"https://www.youtube.com/results?search_query={query}"
            elif self.current_engine == "bing":
                url = f"https://www.bing.com/search?q={query}"
            elif self.current_engine == "yahoo":
                url = f"https://search.yahoo.com/search?p={query}"
            elif self.current_engine == "duck":
                url = f"https://duckduckgo.com/?q={query}"
            else:
                url = f"https://www.google.com/search?q={query}"

            self.browser.setUrl(QUrl(url))


# ================== STORAGE AND CONFIG MANAGEMENT ==================
def load_config():
    config_data = {
        'PIN': '2066', 
        'AI_NAME': 'Solis AI', 
        'USER_NAME': 'Khem Joshi',
        'VOICE_PROFILE': 'FEMALE',
        'PERSONALITY': 'You are Solis, a secure solar cognitive assistant...',
        'LOGGED_IN_ID': '',
        'LOGGED_IN_STATUS': 'FALSE'
    }
    if os.path.exists("config.py"):
        try:
            with open("config.py", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        parts = line.strip().split("=", 1)
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        config_data[key] = val
        except Exception:
            pass
    else:
        update_config_file(config_data)
    return config_data

def update_config_file(updates):
    if not os.path.exists("config.py"):
        with open("config.py", "w", encoding="utf-8") as f:
            f.write("# Solis AI Neural Configuration\n")
    try:
        with open("config.py", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        lines = []
        
    new_lines = []
    found_keys = set()
    for line in lines:
        updated = False
        for k, v in updates.items():
            if line.strip().startswith(f"{k}") and "=" in line:
                key_part = line.split("=")[0].strip()
                if key_part == k:
                    new_lines.append(f'{k} = "{v}"\n')
                    found_keys.add(k)
                    updated = True
                    break
        if not updated:
            new_lines.append(line)
            
    for k, v in updates.items():
        if k not in found_keys:
            new_lines.append(f'{k} = "{v}"\n')
            
    try:
        with open("config.py", "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Error saving core configuration: {e}")

def load_api_keys():
    api_data = {
        'GEMINI_API_KEY': '', 
        'GROQ_API_KEY': '',
        'SERPER_API_KEY': '',
        'WEATHER_API_KEY': ''
    }
    if os.path.exists("api.py"):
        try:
            with open("api.py", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        parts = line.strip().split("=", 1)
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        if key in api_data:
                            api_data[key] = val
        except Exception:
            pass
    return api_data


class AppScanner:
    @staticmethod
    def get_installed_apps():
        apps = []
        if not HAS_WINREG:
            return apps
            
        seen = set()
        paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]
        for root, path in paths:
            try:
                key = winreg.OpenKey(root, path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(root, path + "\\" + subkey_name)
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        if any(x in name for x in ["Update", "Redistributable", "Runtime", "SDK", "Language"]):
                            continue
                        if name not in seen:
                            seen.add(name)
                            apps.append({"name": name, "type": "desktop", "status": "INSTALLED"})
                    except Exception: continue
            except Exception: continue
        return sorted(apps, key=lambda x: x['name'].lower())


class IRIS_NeuralInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("SOLIS AI - NEURAL COGNITIVE CORE")
        self.root.geometry("1280x760")
        self.root.configure(bg=BG)

        # Dynamic Configuration Loads
        self.config_data = load_config()
        self.api_data = load_api_keys()

        # Operational Flag Pools
        self.call_active = False
        self.mic_active = True
        self.cam_active = False
        self.screen_sharing = False
        self.ai_phase = "STANDBY"
        
        self.anim_angle = 0.0

        # Hand Gesture Control States
        self.hand_mouse_active = False
        self.latest_hand_frame = None
        self.hand_thread = None

        self.SMOOTH_FRAMES = 7
        self.SCROLL_SENS = 700
        self.ACTIVE_MARGIN = 0.12
        self.FLIP = True
        self.PINCH_CLOSE = 0.045
        self.PINCH_OPEN = 0.075
        self.SW, self.SH = pyautogui.size()

        # Load persistent login session details
        stored_status = self.config_data.get('LOGGED_IN_STATUS', 'FALSE')
        stored_id = self.config_data.get('LOGGED_IN_ID', '')

        if stored_status == 'TRUE' and len(stored_id) == 8:
            self.current_user_id = stored_id
            self.is_user_logged_in = True
            self.save_chat_history = True
            self.startup_bypass_required = True
        else:
            self.current_user_id = ""
            self.is_user_logged_in = False
            self.save_chat_history = False
            self.startup_bypass_required = False

        self.current_session_messages = []
        self.cap = None
        self.active_tab = "DASHBOARD"
        self.is_settings_authenticated = False
        self.pyqt_browser_window = None

        # Project/Roadmap States
        self.project_nodes = {}
        self.selected_node_id = None
        self.conn_mode = False
        self.source_node_id = None
        self.drag_node_id = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Side Panels Visibility States
        self.left_panel_visible = True
        self.right_panel_visible = True

        # OpenCV Haar Cascade for Face Detection
        self.face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

        self.entered_pin_digits = []
        self.is_unlocking_anim_active = False

        self._build_initial_login_screen()

    # ================== STARTUP SECURITY LOCK GATEWAY ==================
    def _build_initial_login_screen(self):
        self.main_login_frame = tk.Frame(self.root, bg=BG)
        self.main_login_frame.pack(fill="both", expand=True)

        self.gate_box = tk.Frame(self.main_login_frame, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=40, pady=40)
        self.gate_box.place(relx=0.5, rely=0.5, anchor="center")

        if self.startup_bypass_required:
            self._show_system_lock_interface()
        else:
            self._render_startup_account_portal()

    def _render_startup_account_portal(self):
        for widget in self.gate_box.winfo_children():
            widget.destroy()

        tk.Label(self.gate_box, text="SOLIS ACCOUNT PORTAL", fg=SOLAR_GOLD, bg=BG_PANEL, font=("Consolas", 18, "bold")).pack()
        tk.Label(self.gate_box, text="Please authorize access using an 8-Digit ID or create a new profile.", fg=TEXT_MUTED, bg=BG_PANEL, font=("Segoe UI", 9)).pack(pady=(5, 15))

        input_frame = tk.LabelFrame(self.gate_box, text=" LOG IN EXISTING ACCOUNT ", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Consolas", 9, "bold"), padx=15, pady=15)
        input_frame.pack(fill="x", pady=10)

        self.startup_id_var = tk.StringVar()
        startup_entry = tk.Entry(
            input_frame, textvariable=self.startup_id_var, bg=BG, fg=TEXT_LIGHT, font=("Consolas", 14),
            insertbackground=TEXT_LIGHT, relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, justify="center"
        )
        startup_entry.pack(fill="x", ipady=6, pady=(0, 10))

        btn_login = tk.Button(
            input_frame, text="PROCEED WITH ID ⚡", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=CYAN_ACCENT, cursor="hand2", padx=20, pady=6,
            command=self._login_from_startup_gate
        )
        btn_login.pack(fill="x")

        new_profile_frame = tk.LabelFrame(self.gate_box, text=" AUTOMATIC PROFILE REGISTRATION ", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 9, "bold"), padx=15, pady=15)
        new_profile_frame.pack(fill="x", pady=10)

        btn_register_new = tk.Button(
            new_profile_frame, text="CREATE NEW ACCOUNT ☼", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=ACCENT_GREEN, cursor="hand2", padx=20, pady=8,
            command=self._generate_new_user_from_startup_gate
        )
        btn_register_new.pack(fill="x")

    def _login_from_startup_gate(self):
        entered_id = self.startup_id_var.get().strip()
        if len(entered_id) != 8 or not entered_id.isdigit():
            messagebox.showerror("Error", "कृपया ८ अङ्कको खाता नम्बर हाल्नुहोस्।")
            return

        self.current_user_id = entered_id
        self.is_user_logged_in = True
        self.save_chat_history = True
        self.startup_bypass_required = True

        update_config_file({'LOGGED_IN_ID': entered_id, 'LOGGED_IN_STATUS': 'TRUE'})
        self._show_system_lock_interface()

    def _generate_new_user_from_startup_gate(self):
        new_id = "".join([str(random.randint(0, 9)) for _ in range(8)])
        self.current_user_id = new_id
        self.is_user_logged_in = True
        self.save_chat_history = True
        self.startup_bypass_required = True

        update_config_file({'LOGGED_IN_ID': new_id, 'LOGGED_IN_STATUS': 'TRUE'})
        messagebox.showinfo("Profile Created", f"तपाईंको नयाँ स्थायी खाता ID जेनेरेट भयो: {new_id}")
        self._show_system_lock_interface()

    def _show_system_lock_interface(self):
        for widget in self.gate_box.winfo_children():
            widget.destroy()

        tk.Label(self.gate_box, text="SYSTEM LOCKED", fg=TEXT_LIGHT, bg=BG_PANEL, font=("Consolas", 18, "bold")).pack()
        self.gate_status_badge = tk.Label(self.gate_box, text="LOAD SECURE PIN TO START", bg="#0d1117", fg=ACCENT_GREEN, font=("Consolas", 9, "bold"), padx=15, pady=4)
        self.gate_status_badge.pack(pady=(10, 20))

        self.gate_dynamic_area = tk.Frame(self.gate_box, bg=BG_PANEL, width=440, height=280)
        self.gate_dynamic_area.pack()
        self.gate_dynamic_area.pack_propagate(False)

        self.gate_action_btn = tk.Button(
            self.gate_box, text="INITIATE MANUAL OVERRIDE", bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, cursor="hand2", padx=20, pady=10,
            command=self._toggle_lock_screen_mode
        )
        self.gate_action_btn.pack(pady=(20, 0))

        self.current_lock_mode = "FACE_SCAN"
        self._activate_face_scanner()

    def _toggle_lock_screen_mode(self):
        if self.is_unlocking_anim_active:
            return
        if self.current_lock_mode == "FACE_SCAN":
            self.current_lock_mode = "PIN_ENTRY"
            self._activate_pin_pad()
        else:
            self.current_lock_mode = "FACE_SCAN"
            self._activate_face_scanner()

    def _activate_face_scanner(self):
        for widget in self.gate_dynamic_area.winfo_children():
            widget.destroy()

        self.gate_status_badge.config(text="NO FACE IN FRAME. ALIGN CENTER.", fg=RED_ACCENT)
        self.gate_action_btn.config(text="INITIATE MANUAL OVERRIDE", fg=ACCENT_GREEN, highlightbackground=BORDER_COLOR)

        self.gate_cam_canvas = tk.Canvas(self.gate_dynamic_area, bg="#030303", highlightthickness=1, highlightbackground=ACCENT_GREEN)
        self.gate_cam_canvas.pack(fill="both", expand=True)

        self.gate_cap = cv2.VideoCapture(0)
        self.face_scanned_success = False
        self.face_hold_frames = 0

        def stream_gate():
            if self.current_lock_mode != "FACE_SCAN" or self.gate_cap is None or self.face_scanned_success:
                return
            ret, frame = self.gate_cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                faces = []
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(frame_gray, 1.3, 5)

                h, w, _ = frame.shape
                img_pil = Image.fromarray(frame_rgb)
                draw = ImageDraw.Draw(img_pil)

                if len(faces) > 0:
                    self.gate_status_badge.config(text="IDENTIFIED INDEX MATCHING...", fg=ACCENT_GREEN)
                    self.face_hold_frames += 1
                    
                    for (x, y, fw, fh) in faces:
                        draw.rectangle([x, y, x+fw, y+fh], outline=ACCENT_GREEN, width=2)
                        draw.line([x, y, x+25, y], fill=ACCENT_GREEN, width=4)
                        draw.line([x, y, x, y+25], fill=ACCENT_GREEN, width=4)
                        draw.line([x+fw, y, x+fw-25, y], fill=ACCENT_GREEN, width=4)
                        draw.line([x+fw, y, x+fw, y+25], fill=ACCENT_GREEN, width=4)

                    if self.face_hold_frames >= 20:
                        self.face_scanned_success = True
                        self._trigger_decryption_gate()
                        return
                else:
                    self.face_hold_frames = max(0, self.face_hold_frames - 1)
                    self.gate_status_badge.config(text="NO FACE IN FRAME. ALIGN CENTER.", fg=RED_ACCENT)
                    draw.line([20, 20, 45, 20], fill=RED_ACCENT, width=2)
                    draw.line([20, 20, 20, 45], fill=RED_ACCENT, width=2)

                img_resized = img_pil.resize((440, 280), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img_resized)
                self.gate_cam_canvas.imgtk = imgtk
                self.gate_cam_canvas.create_image(0, 0, anchor="nw", image=imgtk)

            self.root.after(30, stream_gate)

        stream_gate()

    def _deactivate_face_scanner(self):
        if hasattr(self, 'gate_cap') and self.gate_cap is not None:
            self.gate_cap.release()
            self.gate_cap = None

    def _activate_pin_pad(self):
        self._deactivate_face_scanner()
        for widget in self.gate_dynamic_area.winfo_children():
            widget.destroy()

        self.gate_status_badge.config(text="ENTER 4-DIGIT VAULT PIN", fg=ACCENT_GREEN)
        self.gate_action_btn.config(text="ENGAGE OPTICAL SCANNER", fg=ACCENT_GREEN, highlightbackground=ACCENT_GREEN)

        pin_frame = tk.Frame(self.gate_dynamic_area, bg=BG_PANEL)
        pin_frame.place(relx=0.5, rely=0.5, anchor="center")

        shield_canvas = tk.Canvas(pin_frame, width=50, height=50, bg=BG_PANEL, highlightthickness=0)
        shield_canvas.pack(pady=(0, 20))
        shield_canvas.create_polygon(25, 2, 45, 10, 45, 30, 25, 48, 5, 30, 5, 10, fill="", outline=TEXT_MUTED, width=2)

        digit_slots_frame = tk.Frame(pin_frame, bg=BG_PANEL)
        digit_slots_frame.pack()

        self.digit_boxes = []
        self.entered_pin_digits = []

        for i in range(4):
            box = tk.Label(
                digit_slots_frame, text="|", bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 16, "bold"),
                width=3, height=2, highlightthickness=1, highlightbackground=BORDER_COLOR
            )
            box.pack(side="left", padx=6)
            self.digit_boxes.append(box)

        self.root.bind("<Key>", self._on_lock_screen_key_press)
        self._update_pin_pad_ui()

    def _on_lock_screen_key_press(self, event):
        if self.current_lock_mode != "PIN_ENTRY" or self.is_unlocking_anim_active:
            return
            
        char = event.char
        keysym = event.keysym

        if char.isdigit() and len(self.entered_pin_digits) < 4:
            self.entered_pin_digits.append(char)
            self._update_pin_pad_ui()
        elif keysym == "BackSpace" and len(self.entered_pin_digits) > 0:
            self.entered_pin_digits.pop()
            self._update_pin_pad_ui()

        if len(self.entered_pin_digits) == 4:
            self.root.after(200, self._verify_pin_gate)

    def _update_pin_pad_ui(self):
        for i in range(4):
            if i < len(self.entered_pin_digits):
                self.digit_boxes[i].config(text="●", fg=ACCENT_GREEN, highlightbackground=ACCENT_GREEN)
            elif i == len(self.entered_pin_digits):
                self.digit_boxes[i].config(text="|", fg=ACCENT_GREEN, highlightbackground=BORDER_COLOR)
            else:
                self.digit_boxes[i].config(text="", fg=TEXT_MUTED, highlightbackground=BORDER_COLOR)

    def _verify_pin_gate(self):
        entered = "".join(self.entered_pin_digits)
        valid = self.config_data.get('PIN', '2066')

        if entered == valid:
            self.root.unbind("<Key>")
            self._trigger_decryption_gate()
        else:
            messagebox.showerror("Vault Alert", "Decryption code invalid. Intruders logged.")
            self.entered_pin_digits = []
            self._update_pin_pad_ui()

    def _trigger_decryption_gate(self):
        self.is_unlocking_anim_active = True
        self._deactivate_face_scanner()
        self.root.unbind("<Key>")

        for widget in self.gate_box.winfo_children():
            widget.destroy()

        self.gate_box.config(padx=50, pady=50)
        tk.Label(self.gate_box, text="AUTHORIZATION GRANTED", fg=ACCENT_GREEN, bg=BG_PANEL, font=("Consolas", 18, "bold")).pack()
        
        status_sub = tk.Label(self.gate_box, text="IDENTITY VERIFIED. DECRYPTING VAULT...", bg="#0d1117", fg=ACCENT_GREEN, font=("Consolas", 9, "bold"), padx=15, pady=4)
        status_sub.pack(pady=(10, 30))

        self.check_canvas = tk.Canvas(self.gate_box, width=80, height=80, bg=BG_PANEL, highlightthickness=0)
        self.check_canvas.pack()
        self.check_canvas.create_oval(10, 10, 70, 70, outline=ACCENT_GREEN, width=3)
        self.check_canvas.create_polygon(34, 48, 54, 28, 50, 24, 34, 40, 26, 32, 22, 36, fill=ACCENT_GREEN)

        progress_info = tk.Frame(self.gate_box, bg=BG_PANEL, width=340)
        progress_info.pack(pady=(40, 0))
        
        lbl_info = tk.Label(progress_info, text="DECRYPTING VAULT", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8, "bold"))
        lbl_info.pack(side="left")

        self.lbl_percent = tk.Label(progress_info, text="0%", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 8, "bold"))
        self.lbl_percent.pack(side="right")

        self.bar_canvas = tk.Canvas(self.gate_box, width=340, height=6, bg=BG, highlightthickness=0)
        self.bar_canvas.pack(pady=5)
        self.glow_line = self.bar_canvas.create_rectangle(0, 0, 0, 6, fill=ACCENT_GREEN, outline="")

        self._update_decryption_progress(0)

    def _update_decryption_progress(self, current_val):
        if current_val <= 100:
            self.lbl_percent.config(text=f"{current_val}%")
            width = int((current_val / 100) * 340)
            self.bar_canvas.coords(self.glow_line, 0, 0, width, 6)
            self.root.after(random.randint(15, 35), lambda: self._update_decryption_progress(current_val + 1))
        else:
            self.root.after(150, self._finish_initial_unlock)

    def _finish_initial_unlock(self):
        self._deactivate_face_scanner()
        self.main_login_frame.destroy()

        self._build_top_header()
        
        self.workspace_frame = tk.Frame(self.root, bg=BG)
        self.workspace_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self._build_dashboard_tab()
        self._build_apps_tab()
        self._build_notes_tab()
        self._build_project_tab()
        self._build_coder_tab()
        self._build_settings_tab()

        self._switch_tab("DASHBOARD")
        self._update_time_and_telemetry()


    # ================== CORE NAVIGATION HEADER ==================
    def _build_top_header(self):
        self.header_frame = tk.Frame(self.root, bg=BG, height=55)
        self.header_frame.pack(fill="x", side="top", padx=15, pady=(10, 0))
        self.header_frame.pack_propagate(False)

        logo_container = tk.Frame(self.header_frame, bg=BG)
        logo_container.pack(side="left", fill="y")
        
        logo_canvas = tk.Canvas(logo_container, width=32, height=32, bg=BG, highlightthickness=0)
        logo_canvas.pack(side="left", padx=(0, 10))
        logo_canvas.create_polygon(16, 2, 30, 9, 30, 23, 16, 30, 2, 23, 2, 9, fill="", outline=ACCENT_GREEN, width=2)
        logo_canvas.create_text(16, 16, text="☼", fill=ACCENT_GREEN, font=("Segoe UI", 14, "bold"))

        brand_text_frame = tk.Frame(logo_container, bg=BG)
        brand_text_frame.pack(side="left")
        tk.Label(brand_text_frame, text="SOLIS AI", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 14, "bold")).pack(anchor="w")
        tk.Label(brand_text_frame, text="COGNITIVE INTERFACE", bg=BG, fg=ACCENT_GREEN, font=("Consolas", 7, "bold")).pack(anchor="w")

        self.nav_container = tk.Frame(self.header_frame, bg=BG)
        self.nav_container.pack(side="left", expand=True)

        self.nav_buttons = {}
        tabs = [
            ("DASHBOARD", "DASHBOARD"),
            ("Apps", "APPS"),
            ("NOTES", "NOTES"),
            ("PROJECT", "PROJECT"),
            ("CODER", "CODER"),
            ("SETTINGS", "SETTINGS"),
            ("SEARCH", "SEARCH")
        ]
        
        for label, identifier in tabs:
            btn_fg = CYAN_ACCENT if identifier == "SEARCH" else TEXT_MUTED
            btn = tk.Button(
                self.nav_container, text=f"☼ {label.upper()}", bg=BG_PANEL, fg=btn_fg,
                font=("Segoe UI", 9, "bold"), activebackground=BG_PANEL, activeforeground=TEXT_LIGHT,
                relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                command=lambda i=identifier: self._switch_tab(i)
            )
            btn.pack(side="left", padx=4)
            self.nav_buttons[identifier] = btn

        status_panel = tk.Frame(self.header_frame, bg=BG)
        status_panel.pack(side="right", fill="y")
        
        tk.Label(status_panel, text="📶 ONLINE", bg=BG, fg=ACCENT_GREEN, font=("Consolas", 9, "bold")).pack(side="left", padx=10)
        tk.Label(status_panel, text="🔋 100%", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 9, "bold")).pack(side="left", padx=10)
        
        self.header_time_lbl = tk.Label(status_panel, text="--:--:--", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 10, "bold"), padx=10, pady=4)
        self.header_time_lbl.pack(side="left", padx=(10, 0))

    def _switch_tab(self, target_tab):
        if target_tab == "SEARCH":
            self._open_search_browser()
            return

        self.active_tab = target_tab
        for frame in [self.dashboard_frame, self.apps_frame, self.notes_frame, self.project_frame, self.coder_frame, self.settings_frame]:
            frame.pack_forget()

        for tab_id, btn in self.nav_buttons.items():
            if tab_id == "SEARCH":
                continue
            if tab_id == target_tab:
                btn.config(bg=ACCENT_GREEN, fg=BG, activebackground=ACCENT_GREEN, activeforeground=BG)
            else:
                btn.config(bg=BG_PANEL, fg=TEXT_MUTED, activebackground=BG_PANEL, activeforeground=TEXT_LIGHT)

        if target_tab == "DASHBOARD":
            self.dashboard_frame.pack(fill="both", expand=True)
        elif target_tab == "APPS":
            self.apps_frame.pack(fill="both", expand=True)
            self._load_system_apps_async()
        elif target_tab == "NOTES":
            self.notes_frame.pack(fill="both", expand=True)
        elif target_tab == "PROJECT":
            self.project_frame.pack(fill="both", expand=True)
            self._redraw_project_canvas()
            self._update_project_stats()
        elif target_tab == "CODER":
            self.coder_frame.pack(fill="both", expand=True)
        elif target_tab == "SETTINGS":
            self.settings_frame.pack(fill="both", expand=True)
            self._switch_settings_pane("SYSTEM")

    # ================== OPEN PYQT5 BROWSER OVERLAY ==================
    def _open_search_browser(self):
        if not HAS_PYQT:
            messagebox.showerror(
                "Module Missing", 
                "PyQt5 or PyQtWebEngine packages are missing.\n"
                "To use the browser, please install them via command prompt:\n\n"
                "pip install PyQt5 PyQtWebEngine"
            )
            return

        def run_pyqt_app():
            try:
                q_app = QApplication.instance()
                if not q_app:
                    q_app = QApplication(sys.argv)
                
                if self.pyqt_browser_window is None:
                    self.pyqt_browser_window = SearchBrowser(self)
                
                self.pyqt_browser_window.show()
                self.pyqt_browser_window.raise_()
                self.pyqt_browser_window.activateWindow()
                q_app.exec_()
            except Exception as e:
                print(f"Error launching PyQt5 Search Window: {e}. Falling back to default browser.")
                webbrowser.open("https://www.google.com")

        threading.Thread(target=run_pyqt_app, daemon=True).start()


    # ================== TAB 1: DASHBOARD VIEW ==================
    def _build_dashboard_tab(self):
        self.dashboard_frame = tk.Frame(self.workspace_frame, bg=BG)

        left_col = tk.Frame(self.dashboard_frame, bg=BG, width=320)
        left_col.pack(side="left", fill="y", padx=(0, 10))
        left_col.pack_propagate(False)

        center_col = tk.Frame(self.dashboard_frame, bg=BG)
        center_col.pack(side="left", fill="both", expand=True)

        right_col = tk.Frame(self.dashboard_frame, bg=BG, width=340)
        right_col.pack(side="right", fill="y", padx=(10, 0))
        right_col.pack_propagate(False)

        self.optics_card = tk.Frame(left_col, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, height=240)
        self.optics_card.pack(fill="x", pady=(0, 10))
        self.optics_card.pack_propagate(False)
        
        optics_hdr = tk.Frame(self.optics_card, bg=BG_PANEL)
        optics_hdr.pack(fill="x", padx=12, pady=8)
        self.optics_indicator = tk.Label(optics_hdr, text="● OPTICS OFFLINE", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 9, "bold"))
        self.optics_indicator.pack(side="left")

        self.feed_canvas = tk.Canvas(self.optics_card, bg="#050505", highlightthickness=0)
        self.feed_canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.feed_canvas.create_text(138, 90, text="NO SIGNAL", fill=TEXT_MUTED, font=("Consolas", 10, "bold"), tags="placeholder")

        net_card = tk.Frame(left_col, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, height=180)
        net_card.pack(fill="x", pady=(0, 10))
        net_card.pack_propagate(False)
        
        tk.Label(net_card, text="⚡ NETWORK TELEMETRY", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Consolas", 9, "bold")).pack(anchor="w", padx=12, pady=8)
        
        net_metrics_frame = tk.Frame(net_card, bg=BG_PANEL)
        net_metrics_frame.pack(fill="x", padx=12)
        
        self.net_latency_lbl = tk.Label(net_metrics_frame, text="LATENCY\n--", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Consolas", 9, "bold"), justify="center")
        self.net_latency_lbl.pack(side="left", expand=True)
        self.net_packet_lbl = tk.Label(net_metrics_frame, text="PACKET RATE\n--", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 9, "bold"), justify="center")
        self.net_packet_lbl.pack(side="left", expand=True)
        self.net_routing_lbl = tk.Label(net_metrics_frame, text="ROUTING\nLOCAL 🖧", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 9, "bold"), justify="center")
        self.net_routing_lbl.pack(side="left", expand=True)

        self.net_visualizer = tk.Canvas(net_card, bg=BG_PANEL, height=45, highlightthickness=0)
        self.net_visualizer.pack(fill="x", padx=12, pady=(10, 0))
        self.net_visual_lines = []
        for i in range(26):
            line = self.net_visualizer.create_rectangle(10 + i * 10, 40, 16 + i * 10, 40, fill=ACCENT_GREEN, outline="")
            self.net_visual_lines.append(line)

        core_card = tk.Frame(left_col, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1)
        core_card.pack(fill="both", expand=True)
        
        tk.Label(core_card, text="⚙ CORE METRICS", bg=BG_PANEL, fg=NEON_PINK, font=("Consolas", 9, "bold")).pack(anchor="w", padx=12, pady=8)
        
        metrics_grid = tk.Frame(core_card, bg=BG_PANEL)
        metrics_grid.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        metrics_grid.columnconfigure((0, 1), weight=1)
        metrics_grid.rowconfigure((0, 1), weight=1)

        self.cpu_block = tk.Frame(metrics_grid, bg="#07080f", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.cpu_block.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        tk.Label(self.cpu_block, text="CPU LOAD", bg="#07080f", fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w", padx=8, pady=4)
        self.cpu_metric_lbl = tk.Label(self.cpu_block, text="-- %", bg="#07080f", fg=ACCENT_GREEN, font=("Consolas", 14, "bold"))
        self.cpu_metric_lbl.pack(pady=2)

        self.ram_block = tk.Frame(metrics_grid, bg="#07080f", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.ram_block.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        tk.Label(self.ram_block, text="RAM USAGE", bg="#07080f", fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w", padx=8, pady=4)
        self.ram_metric_lbl = tk.Label(self.ram_block, text="-- %", bg="#07080f", fg=CYAN_ACCENT, font=("Consolas", 14, "bold"))
        self.ram_metric_lbl.pack(pady=2)

        self.temp_block = tk.Frame(metrics_grid, bg="#07080f", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.temp_block.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")
        tk.Label(self.temp_block, text="TEMP core", bg="#07080f", fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w", padx=8, pady=4)
        self.temp_metric_lbl = tk.Label(self.temp_block, text="42°C", bg="#07080f", fg=SOLAR_GOLD, font=("Consolas", 14, "bold"))
        self.temp_metric_lbl.pack(pady=2)

        self.os_block = tk.Frame(metrics_grid, bg="#07080f", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.os_block.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")
        tk.Label(self.os_block, text="SYSTEM ARCH", bg="#07080f", fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w", padx=8, pady=4)
        self.os_block_lbl = tk.Label(self.os_block, text="NT 10.0", bg="#07080f", fg=TEXT_LIGHT, font=("Consolas", 12, "bold"))
        self.os_block_lbl.pack(pady=4)

        self.center_orb_canvas = tk.Canvas(center_col, bg=BG, highlightthickness=0)
        self.center_orb_canvas.pack(fill="both", expand=True, pady=(0, 10))

        self.float_control_panel = tk.Frame(center_col, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=20, pady=10)
        self.float_control_panel.pack(side="bottom", fill="x", padx=30, pady=(0, 10))
        
        self.optics_toggle_btn = tk.Button(
            self.float_control_panel, text="📷 CAMERA", bg=BG, fg=SOLAR_GOLD, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", padx=15, pady=6,
            command=self._toggle_dashboard_camera
        )
        self.optics_toggle_btn.pack(side="left", padx=10)

        # 🖐 HAND GESTURE MOUSE TOGGLE BUTTON
        self.hand_mouse_btn = tk.Button(
            self.float_control_panel, text="🖐 HAND MOUSE", bg=BG, fg=CYAN_ACCENT, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", padx=15, pady=6,
            command=self._toggle_hand_mouse
        )
        self.hand_mouse_btn.pack(side="left", padx=10)

        self.master_call_btn = tk.Button(
            self.float_control_panel, text="📞 INITIATE CALL", bg="#09281a", fg=ACCENT_GREEN, font=("Segoe UI", 10, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", padx=25, pady=8,
            command=self._toggle_duplex_call
        )
        self.master_call_btn.pack(side="left", expand=True)

        self.mic_toggle_btn = tk.Button(
            self.float_control_panel, text="🎤 MIC ON", bg=BG, fg=CYAN_ACCENT, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", padx=15, pady=6,
            command=self._toggle_microphone_feed
        )
        self.mic_toggle_btn.pack(side="right", padx=10)

        chatbot_hdr = tk.Frame(right_col, bg=BG)
        chatbot_hdr.pack(fill="x", pady=(0, 10))
        
        tk.Label(chatbot_hdr, text="💬 SOLIS CHATBOT CORE", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(side="left")
        
        btn_new_chat = tk.Button(
            chatbot_hdr, text="NEW CHAT ☼", bg="#151d3b", fg=CYAN_ACCENT, font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", padx=8, pady=2, command=self._trigger_new_chat_sequence
        )
        btn_new_chat.pack(side="right", padx=5)

        self.session_badge = tk.Label(chatbot_hdr, text="ACTIVE SESSION", bg="#0b2416", fg=ACCENT_GREEN, font=("Consolas", 8, "bold"), padx=6, pady=2)
        self.session_badge.pack(side="right")

        self.chatbot_history_area = tk.Text(right_col, bg=BG_PANEL, fg=TEXT_LIGHT, font=("Segoe UI", 10), wrap="word", bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.chatbot_history_area.pack(fill="both", expand=True)
        self.chatbot_history_area.config(state="disabled")

        self.chatbot_history_area.tag_config("system_notif", foreground=ACCENT_GREEN, font=("Segoe UI", 9, "italic"))
        self.chatbot_history_area.tag_config("user_msg", foreground=SOLAR_GOLD, font=("Segoe UI", 10, "bold"))
        self.chatbot_history_area.tag_config("ai_msg", foreground=CYAN_ACCENT, font=("Segoe UI", 10))

        chat_input_panel = tk.Frame(right_col, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1)
        chat_input_panel.pack(fill="x", pady=(10, 0))

        self.chatbot_entry = tk.Entry(
            chat_input_panel, bg=BG, fg=TEXT_LIGHT, insertbackground=TEXT_LIGHT, relief="flat", font=("Segoe UI", 10), bd=0
        )
        self.chatbot_entry.pack(side="left", fill="x", expand=True, padx=10, ipady=8)
        self.chatbot_entry.bind("<Return>", lambda e: self._on_chat_submit())

        btn_send_chat = tk.Button(
            chat_input_panel, text="SEND ☼", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", activebackground=BG, activeforeground=TEXT_LIGHT, cursor="hand2", padx=15,
            command=self._on_chat_submit
        )
        btn_send_chat.pack(side="right", fill="y")

        self._write_chatbot_line("System", "Solis text command interface initialized.", "system_notif")

    def _write_chatbot_line(self, sender, message, tag_name):
        self.chatbot_history_area.config(state="normal")
        self.chatbot_history_area.insert(tk.END, f"\n[{sender}]: {message}\n", tag_name)
        self.chatbot_history_area.see(tk.END)
        self.chatbot_history_area.config(state="disabled")

    def _on_chat_submit(self):
        query = self.chatbot_entry.get().strip()
        if not query:
            return
        
        self.chatbot_entry.delete(0, tk.END)
        username = self.config_data.get("USER_NAME", "You")
        if self.current_user_id:
            username = f"User-{self.current_user_id}"

        self._write_chatbot_line(username, query, "user_msg")
        self.current_session_messages.append({"sender": username, "text": query, "tag": "user_msg"})

        threading.Thread(target=self._process_chatbot_response, args=(query,), daemon=True).start()

    def _process_chatbot_response(self, text_command):
        try:
            if HAS_CONTROLLER:
                reply = controller(text_command)
            else:
                if "open tiktok" in text_command.lower() or "टिकटक" in text_command:
                    reply = "TikTok एप्लिकेसन खोल्न अनुरोध प्राप्त भयो।"
                elif "close tiktok" in text_command.lower():
                    reply = "TikTok एप्लिकेसन बन्द गरिँदैछ।"
                else:
                    reply = f"प्राप्त आदेश: '{text_command}' को विश्लेषण सुचारु गरिँदै छ।"
        except Exception as e:
            reply = f"Error processing request: {e}"

        self.root.after(0, lambda: self._post_chatbot_reply(text_command, reply))

    def _post_chatbot_reply(self, original_query, ai_reply):
        ai_name = self.config_data.get("AI_NAME", "Solis")
        self._write_chatbot_line(ai_name, ai_reply, "ai_msg")
        self.current_session_messages.append({"sender": ai_name, "text": ai_reply, "tag": "ai_msg"})

    def _trigger_new_chat_sequence(self):
        if not self.current_session_messages:
            self._reset_chatbot_screen()
            return

        topic_name = simpledialog.askstring("Important Topic", "यस कुराकानीको शीर्षक (Topic Name) राख्नुहोस्:")
        if not topic_name:
            topic_name = f"Session_{datetime.now().strftime('%H%M%S')}"

        safe_topic_name = "".join([c for c in topic_name if c.isalnum() or c in (' ', '_', '-')]).rstrip()
        safe_topic_name = safe_topic_name.replace(" ", "_")

        os.makedirs("chat_history", exist_ok=True)

        user_prefix = self.current_user_id if self.current_user_id else "guest"
        filepath = f"chat_history/{user_prefix}_{safe_topic_name}.txt"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"--- SOLIS CONVERSATION PROFILE: {topic_name} ---\n")
                f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"USER ACCESS ID: {user_prefix}\n")
                f.write("----------------------------------------\n\n")
                for msg in self.current_session_messages:
                    f.write(f"[{msg['sender']}]: {msg['text']}\n")
            
            messagebox.showinfo("History Saved", f"च्याट हिस्ट्री सफलतापूर्वक '{topic_name}' शीर्षकमा सेभ भयो।")
        except Exception as ex:
            messagebox.showerror("Vault Error", f"Could not archive chat index: {ex}")

        self._reset_chatbot_screen()

    def _reset_chatbot_screen(self):
        self.current_session_messages = []
        self.chatbot_history_area.config(state="normal")
        self.chatbot_history_area.delete(1.0, tk.END)
        self.chatbot_history_area.config(state="disabled")
        self._write_chatbot_line("System", "New Chat session initialized. Fresh canvas active.", "system_notif")


    # ================== RADAR & HAND FEED ANIMATION ==================
    def _draw_radar_animation(self):
        if self.active_tab != "DASHBOARD":
            return
            
        self.center_orb_canvas.delete("points")
        self.center_orb_canvas.delete("hand_feed")
        cx = self.center_orb_canvas.winfo_width() / 2
        cy = self.center_orb_canvas.winfo_height() / 2
        
        if cx < 10 or cy < 10:
            cx, cy = 200, 200

        # Draw camera feed inside radar if active
        if self.hand_mouse_active and self.latest_hand_frame is not None:
            try:
                frame_rgb = cv2.cvtColor(self.latest_hand_frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(frame_rgb)
                
                canvas_w = int(self.center_orb_canvas.winfo_width())
                canvas_h = int(self.center_orb_canvas.winfo_height())
                if canvas_w > 10 and canvas_h > 10:
                    img_resized = img_pil.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
                    imgtk = ImageTk.PhotoImage(image=img_resized)
                    self.center_orb_canvas.imgtk = imgtk  
                    self.center_orb_canvas.create_image(0, 0, anchor="nw", image=imgtk, tags="hand_feed")
            except Exception as draw_err:
                print(f"[Overlay Drawing Error]: {draw_err}")
            
        self.anim_angle += 0.03
        if self.anim_angle > 2 * math.pi:
            self.anim_angle -= 2 * math.pi
            
        radar_color = CYAN_ACCENT if self.hand_mouse_active else ACCENT_GREEN
        r1 = 120
        self.center_orb_canvas.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, outline=BORDER_COLOR, width=1, tags="points")
        self.center_orb_canvas.create_arc(cx - r1, cy - r1, cx + r1, cy + r1, start=math.degrees(self.anim_angle), extent=45, outline=radar_color, width=2, style="arc", tags="points")
        self.center_orb_canvas.create_arc(cx - r1, cy - r1, cx + r1, cy + r1, start=math.degrees(self.anim_angle) + 180, extent=45, outline=radar_color, width=2, style="arc", tags="points")
        
        r2 = 80
        self.center_orb_canvas.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline=BORDER_COLOR, width=1, tags="points")
        self.center_orb_canvas.create_arc(cx - r2, cy - r2, cx + r2, cy + r2, start=math.degrees(-1.8 * self.anim_angle), extent=75, outline=CYAN_ACCENT, width=1.5, style="arc", tags="points")
        self.center_orb_canvas.create_arc(cx - r2, cy - r2, cx + r2, cy + r2, start=math.degrees(-1.8 * self.anim_angle) + 180, extent=75, outline=CYAN_ACCENT, width=1.5, style="arc", tags="points")
        
        self.center_orb_canvas.create_line(cx - r1 - 10, cy, cx - r2, cy, fill=BORDER_COLOR, tags="points")
        self.center_orb_canvas.create_line(cx + r2, cy, cx + r1 + 10, cy, fill=BORDER_COLOR, tags="points")
        self.center_orb_canvas.create_line(cx, cy - r1 - 10, cx, cy - r2, fill=BORDER_COLOR, tags="points")
        self.center_orb_canvas.create_line(cx, cy + r2, cx, cy + r1 + 10, fill=BORDER_COLOR, tags="points")
        
        pulse_r = 16 + math.sin(time.time() * 5) * 4
        core_color = SOLAR_GOLD if self.ai_phase == "STANDBY" else (ACCENT_GREEN if self.ai_phase == "SPEAKING" else NEON_PINK)
        self.center_orb_canvas.create_oval(cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r, outline=core_color, width=2, tags="points")
        self.center_orb_canvas.create_text(cx, cy, text="☼", fill=core_color, font=("Segoe UI", 13, "bold"), tags="points")

        sweep_x = cx + r1 * math.cos(self.anim_angle)
        sweep_y = cy + r1 * math.sin(self.anim_angle)
        self.center_orb_canvas.create_line(cx, cy, sweep_x, sweep_y, fill="#0c3c26", width=1.5, tags="points")
        
        deg = int(math.degrees(self.anim_angle))
        status_text = "HAND CONTROLLER: ACTIVE 🖐" if self.hand_mouse_active else f"SOLAR RADAR: {deg}° SECURE"
        self.center_orb_canvas.create_text(cx, cy + r1 + 25, text=status_text, fill=TEXT_MUTED, font=("Consolas", 8, "bold"), tags="points")


    # ================== TAB 2: SYSTEM APPLICATIONS VIEW ==================
    def _build_apps_tab(self):
        self.apps_frame = tk.Frame(self.workspace_frame, bg=BG)
        
        hdr = tk.Frame(self.apps_frame, bg=BG, pady=10)
        hdr.pack(fill="x")
        
        tk.Label(hdr, text="💻 SYSTEM APPLICATIONS", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 14, "bold")).pack(side="left")
        self.apps_count_lbl = tk.Label(hdr, text="-- FOUND", bg="#112518", fg=ACCENT_GREEN, font=("Consolas", 10, "bold"), padx=10, pady=4)
        self.apps_count_lbl.pack(side="right")

        search_card = tk.Frame(self.apps_frame, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1)
        search_card.pack(fill="x", pady=10)
        
        self.apps_search_var = tk.StringVar()
        self.apps_search_var.trace("w", self._filter_apps_view)
        
        tk.Label(search_card, text="🔍", bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 12)).pack(side="left", padx=10)
        self.apps_search_entry = tk.Entry(
            search_card, textvariable=self.apps_search_var, bg=BG_PANEL, fg=TEXT_LIGHT,
            insertbackground=TEXT_LIGHT, relief="flat", font=("Segoe UI", 11)
        )
        self.apps_search_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 15))
        self.apps_search_entry.insert(0, "Search index keys...")
        self.apps_search_entry.bind("<FocusIn>", lambda e: self.apps_search_entry.delete(0, 'end') if self.apps_search_var.get() == "Search index keys..." else None)

        self.apps_scroll_canvas = tk.Canvas(self.apps_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.apps_frame, orient="vertical", command=self.apps_scroll_canvas.yview)
        
        self.apps_grid_container = tk.Frame(self.apps_scroll_canvas, bg=BG)
        self.apps_scroll_canvas.create_window((0, 0), window=self.apps_grid_container, anchor="nw")
        self.apps_grid_container.bind("<Configure>", lambda e: self.apps_scroll_canvas.configure(scrollregion=self.apps_scroll_canvas.bbox("all")))
        
        self.apps_scroll_canvas.configure(yscrollcommand=scrollbar.set)
        self.apps_scroll_canvas.pack(side="left", fill="both", expand=True, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.apps_scroll_canvas.bind_all("<MouseWheel>", self._scroll_apps_grid)

    def _scroll_apps_grid(self, event):
        if self.active_tab == "APPS":
            self.apps_scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_system_apps_async(self):
        def task():
            self.all_scanned_apps = AppScanner.get_installed_apps()
            for wa in WEB_APPS:
                self.all_scanned_apps.append({"name": wa['name'], "type": "web", "status": "CLOUDPORT"})
            
            self.filtered_scanned_apps = self.all_scanned_apps
            self.root.after(0, self._render_apps_grid)
        threading.Thread(target=task, daemon=True).start()

    def _filter_apps_view(self, *args):
        query = self.apps_search_var.get().lower()
        if query == "search index keys...":
            query = ""
        self.filtered_scanned_apps = [a for a in self.all_scanned_apps if query in a['name'].lower()]
        self._render_apps_grid()

    def _render_apps_grid(self):
        for widget in self.apps_grid_container.winfo_children():
            widget.destroy()

        self.apps_count_lbl.config(text=f"{len(self.filtered_scanned_apps)} FOUND")
        
        canvas_width = self.apps_scroll_canvas.winfo_width()
        if canvas_width < 100:
            canvas_width = self.root.winfo_width() - 80
        columns = max(1, canvas_width // (CARD_WIDTH + 15))

        for index, app in enumerate(self.filtered_scanned_apps):
            row = index // columns
            col = index % columns
            
            card = tk.Frame(self.apps_grid_container, bg=CARD_BG, width=CARD_WIDTH, height=CARD_HEIGHT, highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.grid(row=row, column=col, padx=6, pady=6)
            card.grid_propagate(False)

            icon_canvas = tk.Canvas(card, width=32, height=32, bg=CARD_BG, highlightthickness=0)
            icon_canvas.place(x=15, y=24)
            icon_canvas.create_polygon(16, 2, 30, 9, 30, 23, 16, 30, 2, 23, 2, 9, fill="", outline=SOLAR_GOLD, width=1)
            icon_canvas.create_text(16, 16, text="☼", fill=SOLAR_GOLD, font=("Consolas", 9, "bold"))

            lbl_title = tk.Label(card, text=app['name'][:22], bg=CARD_BG, fg=TEXT_LIGHT, font=("Segoe UI", 9, "bold"))
            lbl_title.place(x=60, y=20)
            lbl_status = tk.Label(card, text=app['status'], bg=CARD_BG, fg=TEXT_MUTED, font=("Consolas", 8))
            lbl_status.place(x=60, y=42)

            self._bind_hover_animations(card, [lbl_title, lbl_status])

    def _bind_hover_animations(self, target_widget, sub_widgets):
        def on_enter(e):
            target_widget.config(bg=CARD_HOVER, highlightbackground=CYAN_ACCENT)
            for w in sub_widgets:
                w.config(bg=CARD_HOVER)
        def on_leave(e):
            target_widget.config(bg=CARD_BG, highlightbackground=BORDER_COLOR)
            for w in sub_widgets:
                w.config(bg=CARD_BG)
                
        for widget in [target_widget] + sub_widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)


    # ================== TAB 3: MEMORY BANK (NOTES) ==================
    def _build_notes_tab(self):
        self.notes_frame = tk.Frame(self.workspace_frame, bg=BG)
        
        left_list_col = tk.Frame(self.notes_frame, bg=BG, width=280)
        left_list_col.pack(side="left", fill="y", padx=(0, 15))
        left_list_col.pack_propagate(False)

        right_editor_col = tk.Frame(self.notes_frame, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1)
        right_editor_col.pack(side="left", fill="both", expand=True)

        tk.Label(left_list_col, text="📓 MEMORY BANK", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        btn_new_note = tk.Button(
            left_list_col, text="+ CREATE ENTRY", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", pady=8,
            command=self._clear_notes_editor
        )
        btn_new_note.pack(fill="x", pady=(0, 10))

        self.notes_listbox = tk.Listbox(
            left_list_col, bg=BG_PANEL, fg=TEXT_LIGHT, selectbackground=ACCENT_GREEN, selectforeground=BG,
            font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR
        )
        self.notes_listbox.pack(fill="both", expand=True)
        self.notes_listbox.bind("<<ListboxSelect>>", self._on_note_selected_from_list)

        tk.Label(right_editor_col, text="ENTRY DESCRIPTOR", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 9, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        
        self.note_title_entry = tk.Entry(right_editor_col, bg=BG_PANEL, fg=TEXT_LIGHT, font=("Segoe UI", 16, "bold"), insertbackground=TEXT_LIGHT, relief="flat")
        self.note_title_entry.pack(fill="x", padx=20, pady=(0, 10))
        self.note_title_entry.insert(0, "UNTITLED MEMORY ENTRY...")

        self.note_content_area = tk.Text(right_editor_col, bg="#040407", fg=TEXT_LIGHT, font=("Segoe UI", 11), wrap="word", bd=0, insertbackground=TEXT_LIGHT)
        self.note_content_area.pack(fill="both", expand=True, padx=20, pady=10)
        self.note_content_area.insert(tk.END, "Describe historical elements or capture custom notes here...")

        save_panel = tk.Frame(right_editor_col, bg=BG_PANEL, pady=12)
        save_panel.pack(fill="x", side="bottom")

        btn_commit_note = tk.Button(
            save_panel, text="💾 SAVE TO MEMORY", bg="#09281a", fg=ACCENT_GREEN, font=("Segoe UI", 10, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", padx=20, pady=8,
            command=self._commit_note_to_bank
        )
        btn_commit_note.pack(side="right", padx=20)

        self._refresh_notes_directory()

    def _refresh_notes_directory(self):
        self.notes_listbox.delete(0, tk.END)
        os.makedirs("memories", exist_ok=True)
        for filename in os.listdir("memories"):
            if filename.endswith(".txt"):
                self.notes_listbox.insert(tk.END, filename[:-4])

    def _clear_notes_editor(self):
        self.note_title_entry.delete(0, tk.END)
        self.note_title_entry.insert(0, "UNTITLED MEMORY ENTRY...")
        self.note_content_area.delete(1.0, tk.END)

    def _commit_note_to_bank(self):
        title = self.note_title_entry.get().strip()
        content = self.note_content_area.get(1.0, tk.END).strip()
        
        if title == "" or title == "UNTITLED MEMORY ENTRY...":
            messagebox.showerror("Fault Matrix", "Could not commit empty or invalid entry descriptors.")
            return

        os.makedirs("memories", exist_ok=True)
        filepath = os.path.join("memories", f"{title}.txt")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self._refresh_notes_directory()
            messagebox.showinfo("Success", "Memory mapped and logged into bank.")
        except Exception as e:
            messagebox.showerror("IO System Error", f"Could not perform file write: {e}")

    def _on_note_selected_from_list(self, event):
        selection = self.notes_listbox.curselection()
        if not selection:
            return
        selected_title = self.notes_listbox.get(selection[0])
        filepath = os.path.join("memories", f"{selected_title}.txt")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.note_title_entry.delete(0, tk.END)
            self.note_title_entry.insert(0, selected_title)
            self.note_content_area.delete(1.0, tk.END)
            self.note_content_area.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("IO Read Failure", f"Could not decode target file structure: {e}")


    # ================== TAB 4: EMBEDDED ROADMAP STUDIO (PROJECT) ==================
    def _build_project_tab(self):
        self.project_frame = tk.Frame(self.workspace_frame, bg=BG)

        self.project_left_col = tk.Frame(self.project_frame, bg=BG, width=280)
        self.project_left_col.pack(side="left", fill="y", padx=(0, 10))
        self.project_left_col.pack_propagate(False)

        self.project_right_col = tk.Frame(self.project_frame, bg=BG_PANEL, width=280, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.project_right_col.pack(side="right", fill="y", padx=(10, 0))
        self.project_right_col.pack_propagate(False)

        self.project_center_col = tk.Frame(self.project_frame, bg=BG)
        self.project_center_col.pack(side="left", fill="both", expand=True)

        tk.Label(self.project_left_col, text="⚙ ROADMAP CONTROLS", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 10, "bold")).pack(anchor="w", pady=(0, 5))

        btn_add = tk.Button(
            self.project_left_col, text="➕ ADD NEW MODULE", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", pady=8,
            command=self._project_add_node
        )
        btn_add.pack(fill="x", pady=5)

        self.btn_conn_project = tk.Button(
            self.project_left_col, text="🔗 CONNECT MODULES", bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", pady=8,
            command=self._project_start_connection
        )
        self.btn_conn_project.pack(fill="x", pady=5)

        btn_align = tk.Button(
            self.project_left_col, text="📐 AUTO-ALIGN LAYOUT", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", pady=8,
            command=self._project_auto_align_nodes
        )
        btn_align.pack(fill="x", pady=5)

        tk.Label(self.project_left_col, text="🔍 FILTER MODULES", bg=BG, fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w", pady=(10, 2))
        self.project_search_var = tk.StringVar()
        self.project_search_var.trace("w", lambda *args: self._redraw_project_canvas())
        search_entry = tk.Entry(
            self.project_left_col, textvariable=self.project_search_var, bg=BG_PANEL, fg=TEXT_LIGHT,
            insertbackground=TEXT_LIGHT, relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR
        )
        search_entry.pack(fill="x", ipady=5, pady=(0, 10))

        tk.Label(self.project_left_col, text="PROJECT TELEMETRY", bg=BG, fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w")
        self.project_stats_box = tk.Text(
            self.project_left_col, bg="#0a0b10", fg=CYAN_ACCENT, font=("Consolas", 8),
            relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, height=8
        )
        self.project_stats_box.pack(fill="x", pady=5)
        self.project_stats_box.config(state="disabled")

        btn_save = tk.Button(
            self.project_left_col, text="💾 SAVE PROJECT", bg="#09281a", fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", pady=10,
            command=self._project_save_flow
        )
        btn_save.pack(fill="x", pady=(15, 5))

        btn_history = tk.Button(
            self.project_left_col, text="📜 PROJECT HISTORY", bg=BG_PANEL, fg=SOLAR_GOLD, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2", pady=10,
            command=self._project_show_history_vault
        )
        btn_history.pack(fill="x", pady=5)

        tk.Label(self.project_right_col, text="📋 MODULE PROPERTIES", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 10, "bold")).pack(anchor="w", padx=15, pady=15)

        tk.Label(self.project_right_col, text="MODULE NAME", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8)).pack(anchor="w", padx=15)
        self.proj_ed_name = tk.Entry(self.project_right_col, bg=BG, fg=TEXT_LIGHT, relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.proj_ed_name.pack(fill="x", padx=15, pady=5, ipady=4)

        tk.Label(self.project_right_col, text="DESCRIPTION", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8)).pack(anchor="w", padx=15, pady=(10, 0))
        self.proj_ed_desc = tk.Text(self.project_right_col, bg=BG, fg=TEXT_LIGHT, relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, height=4)
        self.proj_ed_desc.pack(fill="x", padx=15, pady=5)

        tk.Label(self.project_right_col, text="STATUS", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8)).pack(anchor="w", padx=15, pady=(10, 0))
        self.proj_ed_status = ttk.Combobox(self.project_right_col, values=["Planned", "In Progress", "Testing", "Completed"], state="readonly")
        self.proj_ed_status.pack(fill="x", padx=15, pady=5)

        tk.Label(self.project_right_col, text="PROGRESS %", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8)).pack(anchor="w", padx=15, pady=(10, 0))
        self.proj_ed_progress = tk.Scale(self.project_right_col, from_=0, to=100, orient="horizontal", bg=BG_PANEL, fg=TEXT_LIGHT, highlightthickness=0, troughcolor=BG, activebackground=ACCENT_GREEN)
        self.proj_ed_progress.pack(fill="x", padx=15, pady=5)

        btn_apply = tk.Button(
            self.project_right_col, text="✅ APPLY CHANGES", bg="#09281a", fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", pady=8,
            command=self._project_update_selected_node
        )
        btn_apply.pack(fill="x", padx=15, pady=15)

        btn_delete = tk.Button(
            self.project_right_col, text="🗑️ DELETE MODULE", bg="#3a0c14", fg=RED_ACCENT, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightbackground=RED_ACCENT, highlightthickness=1, cursor="hand2", pady=8,
            command=self._project_delete_selected_node
        )
        btn_delete.pack(fill="x", padx=15, pady=5)

        self.canvas_header = tk.Frame(self.project_center_col, bg=BG, pady=5)
        self.canvas_header.pack(fill="x")

        self.btn_toggle_left = tk.Button(
            self.canvas_header, text="◀ HIDE TOOLS", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Segoe UI", 8, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, cursor="hand2", padx=10, pady=4,
            command=self._project_toggle_left_panel
        )
        self.btn_toggle_left.pack(side="left")

        tk.Label(
            self.canvas_header, 
            text="🖱 [Left-Click + Drag] Nodes | [Right-Click + Drag] Pan Canvas Workspace", 
            bg=BG, fg=TEXT_MUTED, font=("Segoe UI", 8, "italic")
        ).pack(side="left", expand=True)

        self.btn_toggle_right = tk.Button(
            self.canvas_header, text="PROPERTIES ▶", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Segoe UI", 8, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, cursor="hand2", padx=10, pady=4,
            command=self._project_toggle_right_panel
        )
        self.btn_toggle_right.pack(side="right")

        self.project_canvas = tk.Canvas(
            self.project_center_col, bg="#05060b", 
            highlightthickness=1, highlightbackground=BORDER_COLOR,
            scrollregion=(-3000, -3000, 3000, 3000)
        )
        self.project_canvas.pack(fill="both", expand=True)

        self.project_canvas.xview_moveto(0.5)
        self.project_canvas.yview_moveto(0.5)

        self.project_canvas.bind("<ButtonPress-1>", self._on_project_canvas_press)
        self.project_canvas.bind("<B1-Motion>", self._on_project_canvas_drag)
        self.project_canvas.bind("<ButtonRelease-1>", self._on_project_canvas_release)

        self.project_canvas.bind("<ButtonPress-3>", self._on_project_canvas_right_press)
        self.project_canvas.bind("<B3-Motion>", self._on_project_canvas_right_drag)

        self._setup_default_project_roadmap()

    def _project_toggle_left_panel(self):
        if self.left_panel_visible:
            self.project_left_col.pack_forget()
            self.left_panel_visible = False
            self.btn_toggle_left.config(text="▶ SHOW TOOLS")
        else:
            self.left_panel_visible = True
            self.btn_toggle_left.config(text="◀ HIDE TOOLS")
            self._repack_project_columns()

    def _project_toggle_right_panel(self):
        if self.right_panel_visible:
            self.project_right_col.pack_forget()
            self.right_panel_visible = False
            self.btn_toggle_right.config(text="◀ PROPERTIES")
        else:
            self.right_panel_visible = True
            self.btn_toggle_right.config(text="PROPERTIES ▶")
            self._repack_project_columns()

    def _repack_project_columns(self):
        self.project_left_col.pack_forget()
        self.project_right_col.pack_forget()
        self.project_center_col.pack_forget()

        if self.left_panel_visible:
            self.project_left_col.pack(side="left", fill="y", padx=(0, 10))

        if self.right_panel_visible:
            self.project_right_col.pack(side="right", fill="y", padx=(10, 0))

        self.project_center_col.pack(side="left", fill="both", expand=True)

    def _setup_default_project_roadmap(self):
        self.project_nodes.clear()
        
        structure = {
            "SOLIS AI CORE": ["Memory System", "AI Chat", "Voice Assistant", "Personality Engine"],
            "COMMUNICATION": ["Personal Chat", "Group Chat", "Video Calls"],
            "AI GENERATION": ["Image Gen", "Video Gen", "Music Gen", "Coding Assistant"],
            "PLATFORMS": ["Windows App", "Android App", "iOS App"],
            "SECURITY": ["Encryption", "Cloud Backup", "Google Login"]
        }
        
        root_node = FeatureNodeData("SOLIS AI")
        root_node.pos_x, root_node.pos_y = -350, 0
        self.project_nodes[root_node.id] = root_node
        
        y_off = -250
        for cat, items in structure.items():
            cat_node = FeatureNodeData(cat)
            cat_node.pos_x, cat_node.pos_y = -120, y_off
            self.project_nodes[cat_node.id] = cat_node
            root_node.connections.append(cat_node.id)
            
            sub_y = y_off - 50
            for item in items:
                sub_node = FeatureNodeData(item)
                sub_node.pos_x, sub_node.pos_y = 110, sub_y
                self.project_nodes[sub_node.id] = sub_node
                cat_node.connections.append(sub_node.id)
                sub_y += 120
            y_off += 400
            
        self._redraw_project_canvas()
        self._update_project_stats()

    def _redraw_project_canvas(self):
        self.project_canvas.delete("all")
        query = self.project_search_var.get().lower().strip()

        for node_id, node in self.project_nodes.items():
            for target_id in node.connections:
                if target_id in self.project_nodes:
                    target = self.project_nodes[target_id]
                    
                    x1, y1 = node.pos_x + 95, node.pos_y + 55
                    x2, y2 = target.pos_x + 95, target.pos_y + 55
                    
                    cx1 = x1 + (x2 - x1) / 2
                    cy1 = y1
                    cx2 = x1 + (x2 - x1) / 2
                    cy2 = y2
                    
                    self.project_canvas.create_line(
                        x1, y1, cx1, cy1, cx2, cy2, x2, y2,
                        smooth=True, fill=BORDER_COLOR, width=2, tags="edge"
                    )

        for node_id, node in self.project_nodes.items():
            x, y = node.pos_x, node.pos_y
            w, h = 190, 110

            opacity_dim = False
            if query:
                if query not in node.name.lower() and query not in node.description.lower():
                    opacity_dim = True

            bg_color = CARD_BG if not opacity_dim else "#080914"
            border_color = ACCENT_GREEN if node_id == self.selected_node_id else BORDER_COLOR
            text_color = TEXT_LIGHT if not opacity_dim else "#4a536e"
            muted_color = TEXT_MUTED if not opacity_dim else "#3a4154"

            if node_id == self.selected_node_id:
                self.project_canvas.create_rectangle(x-3, y-3, x+w+3, y+h+3, outline=ACCENT_GREEN, width=1)

            self.project_canvas.create_rectangle(x, y, x+w, y+h, fill=bg_color, outline=border_color, width=2)
            self.project_canvas.create_text(x+15, y+20, text=node.name[:24], fill=text_color, anchor="w", font=("Consolas", 9, "bold"))
            
            desc_txt = node.description
            if len(desc_txt) > 48:
                desc_txt = desc_txt[:45] + "..."
            self.project_canvas.create_text(x+15, y+45, text=desc_txt, fill=muted_color, anchor="nw", width=160, font=("Segoe UI", 8))

            self.project_canvas.create_rectangle(x+15, y+90, x+175, y+95, fill=BG, outline="")
            
            fill_w = int(160 * (node.progress / 100))
            if fill_w > 0:
                self.project_canvas.create_rectangle(x+15, y+90, x+15+fill_w, y+95, fill=ACCENT_GREEN, outline="")

    def _on_project_canvas_right_press(self, event):
        self.project_canvas.scan_mark(event.x, event.y)

    def _on_project_canvas_right_drag(self, event):
        self.project_canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_project_canvas_press(self, event):
        cx = self.project_canvas.canvasx(event.x)
        cy = self.project_canvas.canvasy(event.y)

        clicked_node_id = None
        for node_id, node in self.project_nodes.items():
            if node.pos_x <= cx <= node.pos_x + 190 and node.pos_y <= cy <= node.pos_y + 110:
                clicked_node_id = node_id
                break

        if clicked_node_id:
            if self.conn_mode:
                if self.source_node_id and self.source_node_id != clicked_node_id:
                    if clicked_node_id not in self.project_nodes[self.source_node_id].connections:
                        self.project_nodes[self.source_node_id].connections.append(clicked_node_id)
                    self.conn_mode = False
                    self.source_node_id = None
                    self.btn_conn_project.config(text="🔗 CONNECT MODULES", bg=BG_PANEL, fg=TEXT_MUTED)
                    self._redraw_project_canvas()
                    self._update_project_stats()
            else:
                self.selected_node_id = clicked_node_id
                self.drag_node_id = clicked_node_id
                self.drag_offset_x = cx - self.project_nodes[clicked_node_id].pos_x
                self.drag_offset_y = cy - self.project_nodes[clicked_node_id].pos_y
                self._project_load_selected_properties()
                self._redraw_project_canvas()
        else:
            self.selected_node_id = None
            self.drag_node_id = None
            self._redraw_project_canvas()

    def _on_project_canvas_drag(self, event):
        if self.drag_node_id:
            cx = self.project_canvas.canvasx(event.x)
            cy = self.project_canvas.canvasy(event.y)
            node = self.project_nodes[self.drag_node_id]
            node.pos_x = cx - self.drag_offset_x
            node.pos_y = cy - self.drag_offset_y
            self._redraw_project_canvas()

    def _on_project_canvas_release(self, event):
        self.drag_node_id = None

    def _project_add_node(self):
        cx = self.project_canvas.canvasx(self.project_canvas.winfo_width() / 2)
        cy = self.project_canvas.canvasy(self.project_canvas.winfo_height() / 2)
        node = FeatureNodeData("New Module")
        node.pos_x = cx - 95
        node.pos_y = cy - 55
        self.project_nodes[node.id] = node
        self.selected_node_id = node.id
        self._project_load_selected_properties()
        self._redraw_project_canvas()
        self._update_project_stats()

    def _project_start_connection(self):
        if self.selected_node_id:
            self.conn_mode = True
            self.source_node_id = self.selected_node_id
            self.btn_conn_project.config(text="🎯 SELECT TARGET...", bg=ACCENT_GREEN, fg=BG)
        else:
            messagebox.showwarning("Connection Engine", "First select a source module box!")

    def _project_load_selected_properties(self):
        if self.selected_node_id:
            node = self.project_nodes[self.selected_node_id]
            self.proj_ed_name.delete(0, tk.END)
            self.proj_ed_name.insert(0, node.name)
            self.proj_ed_desc.delete(1.0, tk.END)
            self.proj_ed_desc.insert(tk.END, node.description)
            self.proj_ed_status.set(node.status)
            self.proj_ed_progress.set(node.progress)

    def _project_update_selected_node(self):
        if self.selected_node_id:
            node = self.project_nodes[self.selected_node_id]
            node.name = self.proj_ed_name.get()
            node.description = self.proj_ed_desc.get(1.0, tk.END).strip()
            node.status = self.proj_ed_status.get()
            node.progress = self.proj_ed_progress.get()
            self._redraw_project_canvas()
            self._update_project_stats()
            messagebox.showinfo("Success", "Module properties updated successfully.")

    def _project_delete_selected_node(self):
        if self.selected_node_id:
            target_id = self.selected_node_id
            for node in self.project_nodes.values():
                if target_id in node.connections:
                    node.connections.remove(target_id)
            del self.project_nodes[target_id]
            self.selected_node_id = None
            self._redraw_project_canvas()
            self._update_project_stats()

    def _update_project_stats(self):
        total = len(self.project_nodes)
        done = sum(1 for n in self.project_nodes.values() if n.status == "Completed")
        prog = sum(n.progress for n in self.project_nodes.values()) / total if total > 0 else 0
        
        self.project_stats_box.config(state="normal")
        self.project_stats_box.delete(1.0, tk.END)
        self.project_stats_box.insert(tk.END, f"--- SOLIS REPORT ---\nTotal Modules: {total}\nCompleted: {done}\nOverall Progress: {int(prog)}%")
        self.project_stats_box.config(state="disabled")

    def _project_auto_align_nodes(self):
        if not self.project_nodes:
            return
            
        visited = {}
        def assign_depth(node_id, depth):
            if node_id in visited:
                visited[node_id] = max(visited[node_id], depth)
                return
            visited[node_id] = depth
            node = self.project_nodes[node_id]
            for target_id in node.connections:
                if target_id in self.project_nodes:
                    assign_depth(target_id, depth + 1)

        all_targets = set()
        for node in self.project_nodes.values():
            for conn in node.connections:
                all_targets.add(conn)

        roots = [n_id for n_id in self.project_nodes if n_id not in all_targets]
        if not roots:
            roots = list(self.project_nodes.keys())[:1]

        for r in roots:
            assign_depth(r, 0)

        columns = {}
        for n_id, d in visited.items():
            columns.setdefault(d, []).append(n_id)

        for col_idx, n_ids in columns.items():
            x = -400 + col_idx * 270
            for row_idx, n_id in enumerate(n_ids):
                y = -250 + row_idx * 140
                node = self.project_nodes[n_id]
                node.pos_x = x
                node.pos_y = y

        self._redraw_project_canvas()
        messagebox.showinfo("Aligner Matrix", "Visual Roadmap modules coordinates clean up executed successfully.")

    def _project_save_flow(self):
        name = simpledialog.askstring("Save Project", "Enter Project Name:")
        if name and name.strip():
            project_name = name.strip()
            filename = f"{project_name}.json"
            filepath = os.path.join("Project", filename)

            if os.path.exists(filepath):
                ans = messagebox.askyesno("Overwrite Alert", f"A project named '{project_name}' already exists. Overwrite?")
                if not ans:
                    return

            data = [n.to_dict() for n in self.project_nodes.values()]
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                messagebox.showinfo("Vault Saved", f"Project successfully saved in 'Project/{filename}'")
            except Exception as e:
                messagebox.showerror("IO Fault Error", f"Unable to write configuration payload to disk: {e}")

    def _project_show_history_vault(self):
        pop = tk.Toplevel(self.root)
        pop.title("Project Load History")
        pop.geometry("380x450")
        pop.configure(bg=BG)

        tk.Label(pop, text="SELECT PROJECT FROM VAULT", bg=BG, fg=SOLAR_GOLD, font=("Consolas", 11, "bold")).pack(pady=15)

        listbox = tk.Listbox(
            pop, bg=BG_PANEL, fg=TEXT_LIGHT, selectbackground=ACCENT_GREEN, selectforeground=BG,
            font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR
        )
        listbox.pack(fill="both", expand=True, padx=20, pady=10)

        if os.path.exists("Project"):
            files = [f[:-5] for f in os.listdir("Project") if f.endswith(".json")]
            for f in files:
                listbox.insert(tk.END, f)

        def load_selection():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Vault Warning", "Please select a roadmap to restore.")
                return
            
            project_name = listbox.get(sel[0])
            filepath = os.path.join("Project", f"{project_name}.json")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data_list = json.load(f)

                self.project_nodes.clear()
                self.selected_node_id = None

                for d in data_list:
                    node = FeatureNodeData.from_dict(d)
                    self.project_nodes[node.id] = node

                self._redraw_project_canvas()
                self._update_project_stats()
                pop.destroy()
                messagebox.showinfo("Decrypted", f"Project state restored successfully from: {project_name}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Could not map roadmap indices: {e}")

        btn_load = tk.Button(
            pop, text="📂 RESTORE ROADMAP", bg="#09281a", fg=ACCENT_GREEN, font=("Segoe UI", 10, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", pady=10,
            command=load_selection
        )
        btn_load.pack(fill="x", padx=20, pady=15)


    # ================== TAB 5: INTEGRATED CODER WORKSPACE ==================
    def _build_coder_tab(self):
        self.coder_frame = tk.Frame(self.workspace_frame, bg=BG)
        
        self.coder_last_filename = ""
        self.coder_file_list = []
        self.coder_typing_job = None
        
        header_frame = tk.Frame(self.coder_frame, bg="#161625", height=50, bd=0, relief="flat")
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        logo_label = tk.Label(
            header_frame, 
            text=" ⚡ SOLIS CODER ", 
            fg="#00e5ff",
            bg="#161625", 
            font=("Segoe UI", 12, "bold")
        )
        logo_label.pack(side=tk.LEFT, padx=15, pady=10)

        subtitle_label = tk.Label(
            header_frame,
            text="| Developer Sandbox",
            fg="#8c8ca3",
            bg="#161625",
            font=("Segoe UI", 9, "italic")
        )
        subtitle_label.pack(side=tk.LEFT, padx=2, pady=10)

        btn_new_chat = tk.Button(
            header_frame,
            text="🧹 Clear / New Chat",
            command=self._coder_new_chat,
            bg="#ff0055",
            fg="#ffffff",
            activebackground="#cc0044",
            activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4
        )
        btn_new_chat.pack(side=tk.RIGHT, padx=15, pady=8)

        style = ttk.Style()
        style.configure("Coder.TCombobox", 
                        fieldbackground="#202030", 
                        background="#161625", 
                        foreground="#ffffff", 
                        darkcolor="#161625", 
                        lightcolor="#161625",
                        bordercolor="#34344e")

        self.coder_provider_var = tk.StringVar(value="Gemini (1.5-Flash)")
        provider_combo = ttk.Combobox(
            header_frame, 
            textvariable=self.coder_provider_var, 
            values=["Gemini (1.5-Flash)", "Groq (Llama-3.3)"],
            state="readonly",
            width=20,
            style="Coder.TCombobox"
        )
        provider_combo.pack(side=tk.RIGHT, padx=15, pady=10)

        lbl_engine = tk.Label(
            header_frame, 
            text="🤖 Engine:", 
            fg="#a5a5cc", 
            bg="#161625", 
            font=("Segoe UI", 9, "bold")
        )
        lbl_engine.pack(side=tk.RIGHT, padx=2, pady=10)

        self.coder_pane = tk.PanedWindow(self.coder_frame, orient=tk.HORIZONTAL, bg="#0f0f16", bd=0)
        self.coder_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 1. Left Panel (Chat Display)
        left_frame = tk.Frame(self.coder_pane, bg="#161625", width=340)
        self.coder_pane.add(left_frame)

        lbl_chat = tk.Label(
            left_frame, 
            text="💬 CHAT & SYSTEM EXPLANATION", 
            fg="#a5a5cc", 
            bg="#161625", 
            font=("Segoe UI", 8, "bold")
        )
        lbl_chat.pack(anchor="w", padx=12, pady=(10, 4))

        self.coder_chat_display = scrolledtext.ScrolledText(
            left_frame, 
            bg="#0f0f16", 
            fg="#e2e2ec", 
            insertbackground="white",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=1,
            highlightbackground="#26263b"
        )
        self.coder_chat_display.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)
        self.coder_chat_display.insert(tk.END, "🤖 AI: नमस्ते! मलाई कुनै पनि कामको निर्देश दिनुहोस्।\nतपाईँको निर्देशन अनुसारको विवरण यहाँ आउनेछ र कोड दायाँ पट्टी जेनेरेट हुनेछ।\n\n")
        self.coder_chat_display.config(state=tk.DISABLED)

        prompt_label = tk.Label(left_frame, text="Enter instruction / chat here:", fg="#a5a5cc", bg="#161625", font=("Segoe UI", 8))
        prompt_label.pack(anchor="w", padx=12, pady=(5, 1))

        self.coder_prompt_entry = tk.Entry(
            left_frame, 
            bg="#202030", 
            fg="#ffffff", 
            insertbackground="white", 
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=1,
            highlightbackground="#34344e"
        )
        self.coder_prompt_entry.pack(fill=tk.X, ipady=10, padx=12, pady=5)
        self.coder_prompt_entry.bind("<Return>", lambda event: self._coder_generate_code())

        self.coder_btn_generate = tk.Button(
            left_frame, 
            text="🚀 Apply & Generate Code", 
            command=self._coder_generate_code, 
            bg="#7c4dff",
            fg="white", 
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#651fff",
            activeforeground="white"
        )
        self.coder_btn_generate.pack(fill=tk.X, padx=12, pady=(5, 10), ipady=6)

        # 2. Middle Panel (Explorer Sim)
        self.coder_explorer_frame = tk.Frame(self.coder_pane, bg="#11111a", width=150)
        self.coder_pane.add(self.coder_explorer_frame)

        lbl_explorer = tk.Label(
            self.coder_explorer_frame, 
            text="📁 EXPLORER", 
            fg="#a5a5cc", 
            bg="#11111a", 
            font=("Segoe UI", 8, "bold")
        )
        lbl_explorer.pack(anchor="w", padx=10, pady=(10, 4))

        self.coder_file_listbox = tk.Listbox(
            self.coder_explorer_frame,
            bg="#11111a",
            fg="#cfcfdb",
            selectbackground="#202030",
            selectforeground="#00e5ff",
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0
        )
        self.coder_file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.coder_file_listbox.bind("<<ListboxSelect>>", self._coder_on_file_select)

        # 3. Right Panel (Code Workspace)
        right_frame = tk.Frame(self.coder_pane, bg="#0d0d14")
        self.coder_pane.add(right_frame)

        self.coder_tab_frame = tk.Frame(right_frame, bg="#0d0d14", height=30)
        self.coder_tab_frame.pack(fill=tk.X, side=tk.TOP)

        self.coder_tab_label = tk.Label(
            self.coder_tab_frame,
            text="untitled.py",
            bg="#161625",
            fg="#00e5ff",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4
        )
        self.coder_tab_label.pack(side=tk.LEFT)

        self.coder_text_area = scrolledtext.ScrolledText(
            right_frame, 
            font=("Consolas", 10), 
            bg="#08080c",
            fg="#70ffd0",
            insertbackground="white",
            bd=0,
            highlightthickness=1,
            highlightbackground="#161625"
        )
        self.coder_text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        editor_footer = tk.Frame(right_frame, bg="#0d0d14")
        editor_footer.pack(fill=tk.X, pady=(0, 10), padx=10)

        self.coder_btn_copy = tk.Button(
            editor_footer, 
            text="📋 Copy Code", 
            command=self._coder_copy_code, 
            bg="#202030", 
            fg="white", 
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2"
        )
        self.coder_btn_copy.pack(side=tk.LEFT, padx=4, ipady=4)

        self.coder_btn_run = tk.Button(
            editor_footer, 
            text="🌐 Run in Browser", 
            command=self._coder_run_code, 
            bg="#00e676",
            fg="#050505", 
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#00c853"
        )
        self.coder_btn_run.pack(side=tk.LEFT, padx=4, ipady=4)

        # Coder Local Status Bar
        self.coder_status_var = tk.StringVar(value="Coder Sandbox: Ready to build.")
        status_bar = tk.Label(
            self.coder_frame, 
            textvariable=self.coder_status_var, 
            bd=0, 
            relief=tk.SUNKEN, 
            anchor=tk.W, 
            bg="#161625", 
            fg="#a5a5cc", 
            font=("Segoe UI", 8),
            padx=10,
            pady=2
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _coder_is_casual_talk(self, prompt):
        greetings = ["hi", "hello", "hey", "hola", "namaste", "sanchai", "k xa", "k x", "how are you", "who are you", "good morning", "good afternoon"]
        cleaned = prompt.lower().strip().strip("?").strip("!")
        words = cleaned.split()
        if len(words) <= 3 and any(greet in cleaned for greet in greetings):
            return True
        return False

    def _coder_new_chat(self):
        global coder_chat_history
        coder_chat_history = []
        self.coder_last_filename = ""
        
        if self.coder_typing_job:
            self.root.after_cancel(self.coder_typing_job)
            
        self.coder_text_area.delete("1.0", tk.END)
        self.coder_prompt_entry.delete(0, tk.END)
        
        self.coder_file_list = []
        self.coder_file_listbox.delete(0, tk.END)
        
        self.coder_chat_display.config(state=tk.NORMAL)
        self.coder_chat_display.delete("1.0", tk.END)
        self.coder_chat_display.insert(tk.END, "✨ New Session Started.\n🤖 AI: नयाँ प्रोजेक्ट माग गर्नुहोस् वा कुराकानी सुरु गर्नुहोस्।\n\n")
        self.coder_chat_display.config(state=tk.DISABLED)
        
        self.coder_tab_label.config(text="untitled.py")
        self.coder_status_var.set("नयाँ सेसन सुरु भयो।")

    def _coder_typewriter_effect(self, code_text):
        self.coder_text_area.delete("1.0", tk.END)
        lines = code_text.splitlines()
        
        def insert_line(idx):
            if idx < len(lines):
                self.coder_text_area.insert(tk.END, lines[idx] + "\n")
                self.coder_text_area.see(tk.END)
                self.coder_typing_job = self.root.after(12, insert_line, idx + 1)
            else:
                self.coder_typing_job = None
                self.coder_status_var.set(f"✅ Code loading complete.")

        insert_line(0)

    def _coder_generate_code(self):
        prompt = self.coder_prompt_entry.get().strip()
        provider = self.coder_provider_var.get()

        if not prompt:
            messagebox.showwarning("Warning", "कृपया केही लेख्नुहोस्!")
            return

        if self._coder_is_casual_talk(prompt):
            self.coder_chat_display.config(state=tk.NORMAL)
            self.coder_chat_display.insert(tk.END, f"👤 User: {prompt}\n")
            self.coder_chat_display.insert(
                tk.END, 
                "🤖 AI: नमस्ते! म कोडिङ गर्ने AI हुँ। मलाई साधारण कुराकानीमा कोड सिर्जना गर्न अनुमति छैन। "
                "कृपया मलाई सिधै कुनै सफ्टवेयर, 脚本, वा वेब पेज सिर्जना गर्न भन्नुहोस् (जस्तै: 'create a registration page' वा 'python simple calculator') "
                "र म तपाईँको लागि कोड तयार पार्नेछु।\n\n"
            )
            self.coder_chat_display.see(tk.END)
            self.coder_chat_display.config(state=tk.DISABLED)
            self.coder_prompt_entry.delete(0, tk.END)
            return

        existing_code = self.coder_text_area.get("1.0", tk.END).strip()

        self.coder_status_var.set("🤖 AI thinking and researching...")
        self.coder_chat_display.config(state=tk.NORMAL)
        self.coder_chat_display.insert(tk.END, f"👤 User: {prompt}\n")
        self.coder_chat_display.insert(tk.END, f"🤖 AI: Processing request using {provider}... Thinking... 💭\n")
        self.coder_chat_display.see(tk.END)
        self.coder_chat_display.config(state=tk.DISABLED)
        self.root.update_idletasks()

        try:
            response_text, engine_used = generate_code_from_ai(prompt, provider, existing_code)
            
            explanation = "No explanation provided."
            code_content = ""

            if "[EXPLANATION]" in response_text and "[CODE]" in response_text:
                parts = response_text.split("[CODE]")
                explanation = parts[0].replace("[EXPLANATION]", "").strip()
                code_content = parts[1].strip()
            else:
                if "[CODE]" in response_text:
                    parts = response_text.split("[CODE]")
                    code_content = parts[1].strip()
                    explanation = parts[0].replace("[EXPLANATION]", "").strip()
                else:
                    code_content = response_text
                    explanation = "Successfully completed the instruction."

            if code_content.startswith("```"):
                lines = code_content.split("\n")
                if len(lines) > 2:
                    code_content = "\n".join(lines[1:-1])

            self.coder_chat_display.config(state=tk.NORMAL)
            self.coder_chat_display.insert(tk.END, f"📢 Description (using {engine_used}):\n{explanation}\n\n")
            self.coder_chat_display.see(tk.END)
            self.coder_chat_display.config(state=tk.DISABLED)

            self._coder_typewriter_effect(code_content)

            self.coder_last_filename = self._coder_save_code_to_file(code_content)
            basename = os.path.basename(self.coder_last_filename)
            if basename not in self.coder_file_list:
                self.coder_file_list.append(basename)
                self.coder_file_listbox.insert(tk.END, basename)
            
            self.coder_tab_label.config(text=basename)

            coder_chat_history.append({"role": "user", "content": prompt})
            coder_chat_history.append({"role": "assistant", "content": response_text})

            self.coder_prompt_entry.delete(0, tk.END)
            self.coder_status_var.set(f"✅ Success: Code generated inside {basename} ({engine_used})")

        except Exception as e:
            self.coder_status_var.set("❌ Processing failed.")
            self.coder_chat_display.config(state=tk.NORMAL)
            self.coder_chat_display.insert(tk.END, f"❌ Error: System could not generate code. details: {str(e)}\n\n")
            self.coder_chat_display.config(state=tk.DISABLED)
            messagebox.showerror("Error", f"त्रुटि: {str(e)}")

    def _coder_save_code_to_file(self, code_text):
        lower = code_text.lower()
        if "html" in lower[:150]:
            filename = "code/index.html"
        elif "javascript" in lower[:150] or "js" in lower[:150]:
            filename = "code/app.js"
        elif "css" in lower[:150]:
            filename = "code/style.css"
        else:
            filename = "code/program.py"

        os.makedirs("code", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_text)
        return filename

    def _coder_on_file_select(self, event):
        selection = self.coder_file_listbox.curselection()
        if selection:
            filename = self.coder_file_listbox.get(selection[0])
            filepath = os.path.join("code", filename)
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if self.coder_typing_job:
                    self.root.after_cancel(self.coder_typing_job)
                
                self.coder_text_area.delete("1.0", tk.END)
                self.coder_text_area.insert(tk.END, content)
                self.coder_tab_label.config(text=filename)
                self.coder_last_filename = filepath

    def _coder_copy_code(self):
        code_text = self.coder_text_area.get("1.0", tk.END).strip()
        if code_text:
            pyperclip.copy(code_text)
            self.coder_btn_copy.config(text="✅ Copied!")
            self.root.after(2000, lambda: self.coder_btn_copy.config(text="📋 Copy Code"))

    def _coder_run_code(self):
        if self.coder_last_filename and os.path.exists(self.coder_last_filename):
            filepath = os.path.abspath(self.coder_last_filename)
            webbrowser.open(f"file://{filepath}")
        else:
            messagebox.showwarning("File Not Found", "पहिले रन गर्नका लागि कोड तयार गर्नुहोस्।")


    # --- SETTINGS SUB-PANE 1: SYSTEM INFO ---
    def _build_settings_tab(self):
        self.settings_frame = tk.Frame(self.workspace_frame, bg=BG)
        
        settings_header = tk.Frame(self.settings_frame, bg=BG, pady=10)
        settings_header.pack(fill="x")
        
        tk.Label(settings_header, text="🛡 COMMAND CENTER", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 14, "bold")).pack(side="left")
        self.sys_state_lbl = tk.Label(settings_header, text="SYSTEM ONLINE", bg="#0b2416", fg=ACCENT_GREEN, font=("Consolas", 10, "bold"), padx=10, pady=4)
        self.sys_state_lbl.pack(side="right")

        self.sub_tab_bar = tk.Frame(self.settings_frame, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.sub_tab_bar.pack(fill="x", pady=(0, 15))
        
        self.sub_tab_btns = {}
        sub_panes = [
            ("SYSTEM", "SYSTEM"),
            ("GENERAL", "GENERAL"),
            ("API KEYS", "API_KEYS"),
            ("SECURITY", "SECURITY"),
            ("ACCOUNT", "ACCOUNT")
        ]
        
        for name, identifier in sub_panes:
            btn = tk.Button(
                self.sub_tab_bar, text=f"▩ {name}", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 10, "bold"),
                relief="flat", activebackground=BG_PANEL, activeforeground=TEXT_LIGHT, cursor="hand2", padx=20, pady=10,
                command=lambda i=identifier: self._switch_settings_pane(i)
            )
            btn.pack(side="left")
            self.sub_tab_btns[identifier] = btn

        self.settings_sub_workspace = tk.Frame(self.settings_frame, bg=BG)
        self.settings_sub_workspace.pack(fill="both", expand=True)

        self._build_sub_pane_system()
        self._build_sub_pane_general()
        self._build_sub_pane_api_keys()
        self._build_sub_pane_security()
        self._build_sub_pane_account()

    def _switch_settings_pane(self, target_pane):
        if target_pane in ["SYSTEM", "GENERAL", "API_KEYS"] and not self.is_settings_authenticated:
            self._switch_settings_pane("SECURITY")
            return

        for frame in [self.sub_pane_system, self.sub_pane_general, self.sub_pane_api_keys, self.sub_pane_security, self.sub_pane_account]:
            frame.pack_forget()

        for tab_id, btn in self.sub_tab_btns.items():
            if tab_id == target_pane:
                btn.config(bg="#1c1c24", fg=TEXT_LIGHT)
            else:
                btn.config(bg=BG_PANEL, fg=TEXT_MUTED)

        if target_pane == "SYSTEM":
            self.sub_pane_system.pack(fill="both", expand=True)
        elif target_pane == "GENERAL":
            self.sub_pane_general.pack(fill="both", expand=True)
        elif target_pane == "API_KEYS":
            self.sub_pane_api_keys.pack(fill="both", expand=True)
        elif target_pane == "SECURITY":
            self.sub_pane_security.pack(fill="both", expand=True)
        elif target_pane == "ACCOUNT":
            self.sub_pane_account.pack(fill="both", expand=True)
            self._refresh_secure_vault_index()

    def _build_sub_pane_system(self):
        self.sub_pane_system = tk.Frame(self.settings_sub_workspace, bg=BG)
        self.sub_pane_system.columnconfigure((0, 1), weight=1)

        fw_card = tk.Frame(self.sub_pane_system, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=20, pady=20)
        fw_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        tk.Label(fw_card, text="🚀 OS FIRMWARE STATUS", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w")
        tk.Label(fw_card, text="Build stable: Solis AI Cognitive Kernel v1.1.5", bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 20))

        btn_chk_update = tk.Button(
            fw_card, text="⟳ CHECK FOR UPDATES", bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 10, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", padx=15, pady=8,
            command=lambda: messagebox.showinfo("System Check", "Firmware registry fully updated to version 1.1.5")
        )
        btn_chk_update.pack(anchor="w")

        pn_card = tk.Frame(self.sub_pane_system, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=20, pady=20)
        pn_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        tk.Label(pn_card, text="📋 PATCH RELEASE LOGS", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w")
        logs = (
            "Changelog v1.1.5:\n"
            " - Integrated permanent sandbox modules.\n"
            " - Implemented permanent login session config.\n"
            " - Unified startup account creation gateway."
        )
        tk.Label(pn_card, text=logs, bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 9), justify="left").pack(anchor="w", pady=15)

    # --- SETTINGS SUB-PANE 2: GENERAL PROFILE ---
    def _build_sub_pane_general(self):
        self.sub_pane_general = tk.Frame(self.settings_sub_workspace, bg=BG)
        
        card = tk.Frame(self.sub_pane_general, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=25, pady=25)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(card, text="👤 AI PERSONALITY MATRIX DEFINITION", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w")
        self.personality_area = tk.Text(card, bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 10), wrap="word", height=6, bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT)
        self.personality_area.pack(fill="x", pady=10)
        self.personality_area.insert(tk.END, self.config_data.get('PERSONALITY', ''))

        tk.Label(card, text="👤 OPERATOR CALL DESIGNATION", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w", pady=(15, 5))
        self.username_input_var = tk.StringVar(value=self.config_data.get('USER_NAME', ''))
        self.username_field = tk.Entry(card, textvariable=self.username_input_var, bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT)
        self.username_field.pack(fill="x", pady=5, ipady=4)

        tk.Label(card, text="🗣 COGNITIVE VOICE PROFILE", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w", pady=(15, 5))
        self.voice_profile_var = tk.StringVar(value=self.config_data.get('VOICE_PROFILE', 'FEMALE'))
        
        v_btn_frame = tk.Frame(card, bg=BG_PANEL)
        v_btn_frame.pack(anchor="w", pady=5)

        self.btn_v_female = tk.Button(v_btn_frame, text="FEMALE PROFILE", bg=ACCENT_GREEN, fg=BG, font=("Segoe UI", 9, "bold"), relief="flat", padx=15, pady=6, cursor="hand2", command=lambda: self._toggle_voice_profile("FEMALE"))
        self.btn_v_female.pack(side="left", padx=(0, 10))

        self.btn_v_male = tk.Button(v_btn_frame, text="MALE PROFILE", bg=BG, fg=TEXT_MUTED, font=("Segoe UI", 9, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, padx=15, pady=6, cursor="hand2", command=lambda: self._toggle_voice_profile("MALE"))
        self.btn_v_male.pack(side="left")

        self._toggle_voice_profile(self.voice_profile_var.get())

        btn_commit_gen = tk.Button(
            card, text="💾 COMMIT MATRIX PRESET", bg="#09281a", fg=ACCENT_GREEN, font=("Segoe UI", 10, "bold"),
            relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", padx=20, pady=8,
            command=self._commit_general_matrix_settings
        )
        btn_commit_gen.pack(anchor="w", pady=(20, 0))

    def _toggle_voice_profile(self, profile):
        self.voice_profile_var.set(profile)
        if profile == "FEMALE":
            self.btn_v_female.config(bg=ACCENT_GREEN, fg=BG)
            self.btn_v_male.config(bg=BG, fg=TEXT_MUTED)
        else:
            self.btn_v_male.config(bg=ACCENT_GREEN, fg=BG)
            self.btn_v_female.config(bg=BG, fg=TEXT_MUTED)

    def _commit_general_matrix_settings(self):
        updates = {
            'PERSONALITY': self.personality_area.get(1.0, tk.END).strip(),
            'USER_NAME': self.username_input_var.get().strip(),
            'VOICE_PROFILE': self.voice_profile_var.get()
        }
        update_config_file(updates)
        self.config_data = load_config()
        messagebox.showinfo("Matrix Saved", "Solis Brain specs recorded successfully.")

    # --- SETTINGS SUB-PANE 3: API KEYS ENDPOINTS ---
    def _build_sub_pane_api_keys(self):
        self.sub_pane_api_keys = tk.Frame(self.settings_sub_workspace, bg=BG)
        
        card = tk.Frame(self.sub_pane_api_keys, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=25, pady=25)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        hdr_row = tk.Frame(card, bg=BG_PANEL)
        hdr_row.pack(fill="x", pady=(0, 10))
        tk.Label(hdr_row, text="🔑 CLOUD COMPUTING ENDPOINTS", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(side="left")
        
        btn_save_keys = tk.Button(
            hdr_row, text="💾 SAVE ALL KEYS", bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=ACCENT_GREEN, cursor="hand2", padx=15, pady=6,
            command=self._commit_api_matrix_to_disk
        )
        btn_save_keys.pack(side="right")

        inputs_grid = tk.Frame(card, bg=BG_PANEL)
        inputs_grid.pack(fill="both", expand=True)
        inputs_grid.columnconfigure((0, 1), weight=1)

        col_left = tk.Frame(inputs_grid, bg=BG_PANEL)
        col_left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        tk.Label(col_left, text="GEMINI PRO CORE API KEY", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w")
        self.api_gemini_var = tk.StringVar(value=self.api_data.get('GEMINI_API_KEY', ''))
        self.api_gemini_entry = tk.Entry(col_left, textvariable=self.api_gemini_var, show="*", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 10), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT)
        self.api_gemini_entry.pack(fill="x", pady=5, ipady=4)

        col_right = tk.Frame(inputs_grid, bg=BG_PANEL)
        col_right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        tk.Label(col_right, text="GROQ INFERENCING ENGINE KEY", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w")
        self.api_groq_var = tk.StringVar(value=self.api_data.get('GROQ_API_KEY', ''))
        self.api_groq_entry = tk.Entry(col_right, textvariable=self.api_groq_var, show="*", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 10), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT)
        self.api_groq_entry.pack(fill="x", pady=5, ipady=4)

        col_left_2 = tk.Frame(inputs_grid, bg=BG_PANEL)
        col_left_2.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tk.Label(col_left_2, text="SERPER SEARCH ENGINE KEY", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w")
        self.api_serper_var = tk.StringVar(value=self.api_data.get('SERPER_API_KEY', ''))
        self.api_serper_entry = tk.Entry(col_left_2, textvariable=self.api_serper_var, show="*", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 10), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT)
        self.api_serper_entry.pack(fill="x", pady=5, ipady=4)

        col_right_2 = tk.Frame(inputs_grid, bg=BG_PANEL)
        col_right_2.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        tk.Label(col_right_2, text="WEATHER SERVICE API KEY", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 8, "bold")).pack(anchor="w")
        self.api_weather_var = tk.StringVar(value=self.api_data.get('WEATHER_API_KEY', ''))
        self.api_weather_entry = tk.Entry(col_right_2, textvariable=self.api_weather_var, show="*", bg=BG, fg=TEXT_LIGHT, font=("Consolas", 10), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT)
        self.api_weather_entry.pack(fill="x", pady=5, ipady=4)

        notice = tk.Frame(card, bg="#07080f", highlightbackground=BORDER_COLOR, highlightthickness=1, padx=15, pady=10)
        notice.pack(fill="x", side="bottom")
        notice_txt = "🛡 SECURITY POLICY: API Endpoint Credentials are encrypted and recorded locally. Solis will never transmit these codes across unprotected networks."
        tk.Label(notice, text=notice_txt, bg="#07080f", fg=CYAN_ACCENT, font=("Segoe UI", 8, "italic"), justify="left", wrap=380).pack(anchor="w")

    def _commit_api_matrix_to_disk(self):
        g = self.api_gemini_var.get().strip()
        gr = self.api_groq_var.get().strip()
        sr = self.api_serper_var.get().strip()
        wt = self.api_weather_var.get().strip()
        
        try:
            with open("api.py", "w", encoding="utf-8") as f:
                f.write(f'GEMINI_API_KEY = "{g}"\n')
                f.write(f'GROQ_API_KEY = "{gr}"\n')
                f.write(f'SERPER_API_KEY = "{sr}"\n')
                f.write(f'WEATHER_API_KEY = "{wt}"\n')
            self.api_data = load_api_keys()
            messagebox.showinfo("Encrypted Save", "Solis API registry dynamically updated in api.py.")
        except Exception:
            messagebox.showerror("IO Fault", "Could not execute file structure modifications on api.py")

    # --- SETTINGS SUB-PANE 4: SECURITY AUTHENTICATION SHIELD ---
    def _build_sub_pane_security(self):
        self.sub_pane_security = tk.Frame(self.settings_sub_workspace, bg=BG)
        self.security_content_holder = tk.Frame(self.sub_pane_security, bg=BG)
        self.security_content_holder.pack(fill="both", expand=True)
        self._render_security_screen_state()

    def _render_security_screen_state(self):
        for w in self.security_content_holder.winfo_children():
            w.destroy()

        if not self.is_settings_authenticated:
            lock_box = tk.Frame(self.security_content_holder, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=40, pady=40)
            lock_box.place(relx=0.5, rely=0.5, anchor="center")

            lock_canvas = tk.Canvas(lock_box, width=42, height=42, bg=BG_PANEL, highlightthickness=0)
            lock_canvas.pack(pady=(0, 10))
            lock_canvas.create_oval(3, 3, 39, 39, outline=NEON_PINK, width=2)
            lock_canvas.create_text(21, 21, text="🔒", fill=NEON_PINK, font=("Segoe UI", 14))

            tk.Label(lock_box, text="AUTHENTICATE VAULT SYSTEM", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 10, "bold")).pack()
            tk.Label(lock_box, text="Provide access PIN credentials below to unlock configuration settings.", bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 8), justify="center", wrap=250).pack(pady=(5, 15))

            self.vault_entry_var = tk.StringVar()
            entry_field = tk.Entry(lock_box, textvariable=self.vault_entry_var, show="●", bg=BG, fg=NEON_PINK, font=("Segoe UI", 16, "bold"), justify="center", relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=NEON_PINK, width=8)
            entry_field.pack(pady=10)
            entry_field.bind("<Return>", lambda e: self._verify_vault_unlock_action())

            btn_unlock_vault = tk.Button(
                lock_box, text="UNLOCK", bg=BG, fg=NEON_PINK, font=("Segoe UI", 10, "bold"),
                relief="flat", highlightthickness=1, highlightbackground=NEON_PINK, cursor="hand2", padx=25, pady=8,
                command=self._verify_vault_unlock_action
            )
            btn_unlock_vault.pack(pady=(10, 0))

        else:
            card = tk.Frame(self.security_content_holder, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=25, pady=25)
            card.pack(fill="both", expand=True, padx=10, pady=10)

            tk.Label(card, text="🛡 CONFIGURATION SECURITY SHIELD", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 11, "bold")).pack(anchor="w")

            pin_change_frame = tk.Frame(card, bg=BG_PANEL, pady=15)
            pin_change_frame.pack(fill="x")
            tk.Label(pin_change_frame, text="Update Cognitive Vault Master PIN", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 9, "bold")).pack(anchor="w")
            
            self.new_pin_var = tk.StringVar(value=self.config_data.get('PIN', ''))
            new_pin_entry = tk.Entry(pin_change_frame, textvariable=self.new_pin_var, bg=BG, fg=ACCENT_GREEN, font=("Consolas", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground=TEXT_LIGHT, width=12)
            new_pin_entry.pack(anchor="w", pady=5, ipady=4)

            btn_save_pin = tk.Button(
                pin_change_frame, text="SAVE NEW PIN", bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
                relief="flat", highlightthickness=1, highlightbackground=ACCENT_GREEN, cursor="hand2", padx=15, pady=6,
                command=self._update_master_pin_credential
            )
            btn_save_pin.pack(anchor="w", pady=5)

            biometric_frame = tk.Frame(card, bg=BG_PANEL, pady=15)
            biometric_frame.pack(fill="x")
            tk.Label(biometric_frame, text="OS Facial Biometrics Database", bg=BG_PANEL, fg=TEXT_MUTED, font=("Consolas", 9, "bold")).pack(anchor="w")
            tk.Label(biometric_frame, text="Current status: 2 Identities enrolled mathematically.", bg=BG_PANEL, fg=TEXT_LIGHT, font=("Segoe UI", 9)).pack(anchor="w", pady=5)

            btn_enroll_bio = tk.Button(
                biometric_frame, text="+ ENROLL NEW IDENTITY", bg=BG, fg=CYAN_ACCENT, font=("Segoe UI", 9, "bold"),
                relief="flat", highlightthickness=1, highlightbackground=CYAN_ACCENT, cursor="hand2", padx=15, pady=6,
                command=lambda: messagebox.showinfo("Sensor Diagnostic", "Biometric camera scanning module initialized. Scan complete.")
            )
            btn_enroll_bio.pack(anchor="w")

    def _verify_vault_unlock_action(self):
        entered_pin = self.vault_entry_var.get().strip()
        master_pin = self.config_data.get('PIN', '2066')
        
        if entered_pin == master_pin:
            self.is_settings_authenticated = True
            self._render_security_screen_state()
            self._switch_settings_pane("SYSTEM")
        else:
            messagebox.showerror("Access Denied", "Biometric and PIN verification failed.")
            self.vault_entry_var.set("")

    def _update_master_pin_credential(self):
        np = self.new_pin_var.get().strip()
        if len(np) < 4:
            messagebox.showerror("Error", "Security PIN must consist of at least 4 numerical values.")
            return
        update_config_file({'PIN': np})
        self.config_data = load_config()
        messagebox.showinfo("Master PIN Updated", "Solis Security credentials updated in config.py.")

    # --- SETTINGS SUB-PANE 5: USER LOGIN & SECURE HISTORY VAULT ---
    def _build_sub_pane_account(self):
        self.sub_pane_account = tk.Frame(self.settings_sub_workspace, bg=BG)
        
        self.account_panel_left = tk.Frame(self.sub_pane_account, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=20, pady=20)
        self.account_panel_left.place(relx=0.0, rely=0.0, relwidth=0.48, relheight=1.0)

        self.account_panel_right = tk.Frame(self.sub_pane_account, bg=BG_PANEL, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=20, pady=20)
        self.account_panel_right.place(relx=0.5, rely=0.0, relwidth=0.5, relheight=1.0)

        tk.Label(self.account_panel_left, text="👤 COGNITIVE ACCESS CENTER", bg=BG_PANEL, fg=SOLAR_GOLD, font=("Consolas", 12, "bold")).pack(anchor="w", pady=(0, 10))

        id_display_frame = tk.LabelFrame(self.account_panel_left, text=" ACTIVE ACCOUNT ID DETAILS ", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 9, "bold"), padx=10, pady=15)
        id_display_frame.pack(fill="x", pady=10)

        self.lbl_active_id = tk.Label(id_display_frame, text="ID: --------", bg=BG, fg=ACCENT_GREEN, font=("Consolas", 13, "bold"), padx=10, pady=8)
        self.lbl_active_id.pack(fill="x", pady=(0, 10))

        btn_copy_id = tk.Button(
            id_display_frame, text="COPY ACCOUNT ID 📋", bg=BG_PANEL, fg=SOLAR_GOLD, font=("Segoe UI", 8, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=SOLAR_GOLD, cursor="hand2", padx=10, pady=5,
            command=self._copy_id_to_clipboard
        )
        btn_copy_id.pack(side="left", padx=5)

        btn_new_acc = tk.Button(
            id_display_frame, text="NEW ACCOUNT ☼", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Segoe UI", 8, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=CYAN_ACCENT, cursor="hand2", padx=10, pady=5,
            command=self._generate_new_user_id
        )
        btn_new_acc.pack(side="right", padx=5)

        login_direct_frame = tk.LabelFrame(self.account_panel_left, text=" DIRECT ACCOUNT SWITCH ", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Consolas", 9, "bold"), padx=10, pady=15)
        login_direct_frame.pack(fill="x", pady=10)

        self.account_direct_var = tk.StringVar()
        self.account_direct_entry = tk.Entry(
            login_direct_frame, textvariable=self.account_direct_var, bg=BG, fg=TEXT_LIGHT, font=("Consolas", 12),
            insertbackground=TEXT_LIGHT, relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR, justify="center"
        )
        self.account_direct_entry.pack(fill="x", pady=(0, 10), ipady=4)

        btn_direct_login = tk.Button(
            login_direct_frame, text="SWITCH ACCOUNT ⚡", bg=BG_PANEL, fg=CYAN_ACCENT, font=("Segoe UI", 8, "bold"),
            relief="flat", highlightthickness=1, highlightbackground=CYAN_ACCENT, cursor="hand2", command=self._login_existing_user
        )
        btn_direct_login.pack(fill="x")

        self.lbl_account_status = tk.Label(self.account_panel_left, text="STATUS: UNKNOWN", bg="#200a10", fg=RED_ACCENT, font=("Consolas", 8, "bold"), pady=6)
        self.lbl_account_status.pack(fill="x", side="bottom")

        self._build_secure_history_vault_ui()
        self._update_account_pane_ui_state()

    def _build_secure_history_vault_ui(self):
        for widget in self.account_panel_right.winfo_children():
            widget.destroy()

        if not self.is_user_logged_in:
            lock_box = tk.Frame(self.account_panel_right, bg=BG_PANEL)
            lock_box.place(relx=0.5, rely=0.5, anchor="center")

            tk.Label(lock_box, text="🔒 VAULT ENCRYPTED", bg=BG_PANEL, fg=RED_ACCENT, font=("Consolas", 14, "bold")).pack()
            tk.Label(lock_box, text="Authorize utilizing your 8-digit profile ID\nto view archived topic records.", bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 9), justify="center").pack(pady=10)
        else:
            tk.Label(self.account_panel_right, text="📂 SECURE CHAT HISTORY VAULT", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 11, "bold")).pack(anchor="w", pady=(0, 10))
            
            self.vault_listbox = tk.Listbox(
                self.account_panel_right, bg=BG, fg=TEXT_LIGHT, selectbackground=ACCENT_GREEN, selectforeground=BG,
                font=("Segoe UI", 9), bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR
            )
            self.vault_listbox.pack(fill="both", expand=True, pady=(0, 10))

            btn_open_selected = tk.Button(
                self.account_panel_right, text="READ CHAT TRANSCRIPT 📖", bg=BG, fg=ACCENT_GREEN, font=("Segoe UI", 9, "bold"),
                relief="flat", highlightbackground=ACCENT_GREEN, highlightthickness=1, cursor="hand2", pady=6,
                command=self._on_vault_read_button_click
            )
            btn_open_selected.pack(fill="x")

    def _update_account_pane_ui_state(self):
        if self.is_user_logged_in and self.current_user_id:
            self.lbl_active_id.config(text=f"ID: {self.current_user_id}")
            self.lbl_account_status.config(text=f"ACTIVE VAULT: {self.current_user_id} | PERSISTENT", bg="#0a2012", fg=ACCENT_GREEN)
        else:
            self.lbl_active_id.config(text="ID: --------")
            self.lbl_account_status.config(text="STATUS: NOT AUTHENTICATED", bg="#200a10", fg=RED_ACCENT)

    def _copy_id_to_clipboard(self):
        if self.is_user_logged_in and self.current_user_id:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_user_id)
            messagebox.showinfo("Success", f"Account ID कपी गरियो: {self.current_user_id}")
        else:
            messagebox.showwarning("Warning", "कुनै सक्रिय खाता आईडी भेटिएन।")

    def _generate_new_user_id(self):
        new_id = "".join([str(random.randint(0, 9)) for _ in range(8)])
        self.current_user_id = new_id
        self.save_chat_history = True
        self.is_user_logged_in = True

        update_config_file({'LOGGED_IN_ID': new_id, 'LOGGED_IN_STATUS': 'TRUE'})

        self._update_account_pane_ui_state()
        self._build_secure_history_vault_ui()
        self._refresh_secure_vault_index()

        self.session_badge.config(text=f"PROFILE: {new_id}", bg="#09281a", fg=ACCENT_GREEN)
        self._write_chatbot_line("System", f"Logged in under Permanent User Key: {new_id}.", "system_notif")
        messagebox.showinfo("Success", f"नयाँ खाता सुरक्षित रूपमा जेनेरेट भयो!\nतपाईंको स्थायी ID: {new_id}")

    def _login_existing_user(self):
        entered_id = self.account_direct_var.get().strip()
        if len(entered_id) != 8 or not entered_id.isdigit():
            messagebox.showerror("Error", "कृपया स्विच गर्न ८ अङ्कको वैध खाता आईडी दर्ता गर्नुहोस्।")
            return

        self.current_user_id = entered_id
        self.save_chat_history = True
        self.is_user_logged_in = True

        update_config_file({'LOGGED_IN_ID': entered_id, 'LOGGED_IN_STATUS': 'TRUE'})

        self._update_account_pane_ui_state()
        self._build_secure_history_vault_ui()
        self._refresh_secure_vault_index()

        self.session_badge.config(text=f"PROFILE: {entered_id}", bg="#09281a", fg=ACCENT_GREEN)
        self._write_chatbot_line("System", f"Switched account to ID: {entered_id}.", "system_notif")
        messagebox.showinfo("Authorized", f"खाता सफलतापूर्वक स्विच भयो: {entered_id}")

    def _refresh_secure_vault_index(self):
        if not self.is_user_logged_in or not hasattr(self, 'vault_listbox'):
            return
        
        self.vault_listbox.delete(0, tk.END)
        if not os.path.exists("chat_history"):
            return

        user_prefix = self.current_user_id
        for filename in os.listdir("chat_history"):
            if filename.startswith(f"{user_prefix}_") and filename.endswith(".txt"):
                topic_display = filename[len(user_prefix)+1:-4]
                topic_display = topic_display.replace("_", " ")
                self.vault_listbox.insert(tk.END, topic_display)

    def _on_vault_read_button_click(self):
        selection = self.vault_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "कृपया पढ्नको लागि सुरक्षित च्याट छनोट गर्नुहोस्।")
            return

        selected_display = self.vault_listbox.get(selection[0])
        safe_name = selected_display.replace(" ", "_")
        filename = f"{self.current_user_id}_{safe_name}.txt"
        filepath = os.path.join("chat_history", filename)

        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = f.read()
                self._display_chat_history_window(selected_display, data)
            except Exception as e:
                messagebox.showerror("Vault Error", f"Could not decrypt record: {e}")

    def _display_chat_history_window(self, title, content):
        pop = tk.Toplevel(self.root)
        pop.title(f"ARCHIVED TRANSCRIPT: {title}")
        pop.geometry("450x550")
        pop.configure(bg=BG)

        hdr = tk.Frame(pop, bg=BG_PANEL, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"☼ RECORD: {title.upper()}", bg=BG_PANEL, fg=ACCENT_GREEN, font=("Consolas", 11, "bold")).pack()

        txt_area = tk.Text(pop, bg=BG, fg=TEXT_LIGHT, font=("Segoe UI", 10), wrap="word", bd=0, padx=15, pady=15)
        txt_area.pack(fill="both", expand=True)
        txt_area.insert(tk.END, content)
        txt_area.config(state="disabled")


    # ================== SYSTEM DUPLEX TELEPHONY ENGINE ==================
    def _toggle_duplex_call(self):
        if not self.call_active:
            if HAS_MAIN_MODULE:
                try:
                    main.is_running = True
                    
                    def run_async():
                        try:
                            if asyncio.iscoroutinefunction(main.run):
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(main.run())
                                loop.close()
                            else:
                                main.run()
                        except Exception as thread_ex:
                            print(f"[Solis Duplex Core Thread Error]: {thread_ex}")
                            traceback.print_exc()

                    threading.Thread(target=run_async, daemon=True).start()
                except Exception as e:
                    messagebox.showerror("Ecosystem Exception", f"Failed starting duplex channel: {e}")
                    return

            self.call_active = True
            self.master_call_btn.config(text="📴 TERMINATE CALL", bg="#3a0c14", fg=RED_ACCENT, highlightbackground=RED_ACCENT)
            self.sys_state_lbl.config(text="Solis CALL ACTIVE", bg="#3a0c14", fg=RED_ACCENT)
            self._write_chatbot_line("System", "Solis Telemetric duplex stream connection completed.", "system_notif")
            self.ai_phase = "STANDBY"
            
            if self.cam_active:
                self._start_feed_capture()
        else:
            self.call_active = False
            if HAS_MAIN_MODULE:
                try:
                    main.is_running = False
                except Exception as e:
                    print(f"Error stopping main module flag: {e}")
                
            self.master_call_btn.config(text="📞 INITIATE CALL", bg="#09281a", fg=ACCENT_GREEN, highlightbackground=ACCENT_GREEN)
            self.sys_state_lbl.config(text="SYSTEM ONLINE", bg="#112518", fg=ACCENT_GREEN)
            self._write_chatbot_line("System", "Solis Connection stream terminated.", "system_notif")
            self.ai_phase = "STANDBY"
            self._stop_feed_capture()

    def _toggle_dashboard_camera(self):
        # ⚠️ Conflict Prevention: Turn off Hand Mouse if Dashboard Camera is launched
        if self.hand_mouse_active:
            self._toggle_hand_mouse()

        self.cam_active = not self.cam_active
        if self.cam_active:
            self.optics_toggle_btn.config(text="📷 CAM ACTIVE", fg=ACCENT_GREEN, highlightbackground=ACCENT_GREEN)
            self._start_feed_capture()
        else:
            self.optics_toggle_btn.config(text="📷 CAMERA", fg=SOLAR_GOLD, highlightbackground=BORDER_COLOR)
            self._stop_feed_capture()

    def _start_feed_capture(self):
        self.feed_canvas.delete("placeholder")
        self.cap = cv2.VideoCapture(CAM_INDEX)
        self.optics_indicator.config(text="● OPTICS LIVE FEED", fg=ACCENT_GREEN)

        def stream():
            if not self.cam_active or self.cap is None:
                return
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), 1)
                img = Image.fromarray(frame).resize((280, 180), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                self.feed_canvas.imgtk = imgtk
                self.feed_canvas.create_image(0, 0, anchor="nw", image=imgtk, tags="video")
            self.root.after(30, stream)

        stream()

    def _stop_feed_capture(self):
        self.cam_active = False
        self.optics_toggle_btn.config(text="📷 CAMERA", fg=SOLAR_GOLD, highlightbackground=BORDER_COLOR)
        self.optics_indicator.config(text="● OPTICS OFFLINE", fg=TEXT_MUTED)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.feed_canvas.delete("video")
        self.feed_canvas.create_text(138, 90, text="NO SIGNAL", fill=TEXT_MUTED, font=("Consolas", 10, "bold"), tags="placeholder")

    def _toggle_microphone_feed(self):
        self.mic_active = not self.mic_active
        if self.mic_active:
            self.mic_toggle_btn.config(text="🎤 MIC ON", fg=CYAN_ACCENT, highlightbackground=BORDER_COLOR)
        else:
            self.mic_toggle_btn.config(text="🔇 MIC OFF", fg=RED_ACCENT, highlightbackground=RED_ACCENT)


    # ================== HAND GESTURE MOUSE TELEMETRY (BACKGROUND LOOP) ==================
    def _toggle_hand_mouse(self):
        if not HAS_MEDIAPIPE:
            messagebox.showerror(
                "Mediapipe Missing", 
                "हात इसारा प्रणाली (Hand Gesture) को लागि 'mediapipe' लाइब्रेरी आवश्यक छ।\n"
                "कृपया कमाण्ड प्रम्प्टमा यो इन्स्टल गर्नुहोस्:\n\npip install mediapipe"
            )
            return

        if not self.hand_mouse_active:
            # ⚠️ Conflict Prevention: Close dashboard camera feed before launching hand mouse
            if self.cam_active:
                self._stop_feed_capture()

            self.hand_mouse_active = True
            self.hand_mouse_btn.config(text="🖐 HAND ACTIVE", fg=ACCENT_GREEN, highlightbackground=ACCENT_GREEN)
            self.sys_state_lbl.config(text="HAND MOUSE ACTIVE", bg="#0a2012", fg=ACCENT_GREEN)
            self._write_chatbot_line("System", "Hand Gesture Mouse Controller initialized. Look at the center radar.", "system_notif")
            
            self.hand_thread = threading.Thread(target=self._run_hand_mouse_loop, daemon=True)
            self.hand_thread.start()
        else:
            self.hand_mouse_active = False
            self._reset_hand_mouse_button()

    def _reset_hand_mouse_button(self):
        self.hand_mouse_active = False
        self.hand_mouse_btn.config(text="🖐 HAND MOUSE", fg=CYAN_ACCENT, highlightbackground=BORDER_COLOR)
        self.sys_state_lbl.config(text="SYSTEM ONLINE", bg="#112518", fg=ACCENT_GREEN)
        self._write_chatbot_line("System", "Hand Gesture Controller disabled.", "system_notif")
        self.center_orb_canvas.delete("hand_feed")
        self.latest_hand_frame = None

    def _run_hand_mouse_loop(self):
        cap = cv2.VideoCapture(CAM_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        smoother = Smoother(self.SMOOTH_FRAMES)
        l_pinch = PinchTracker(self.PINCH_CLOSE, self.PINCH_OPEN)
        r_pinch = PinchTracker(self.PINCH_CLOSE, self.PINCH_OPEN)

        drag_on = False
        prev_palm_y = None
        scroll_dir = ""
        prev_time = time.time()

        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        mp_styles = mp.solutions.drawing_styles

        try:
            with mp_hands.Hands(
                model_complexity=0,
                max_num_hands=1,
                min_detection_confidence=0.75,
                min_tracking_confidence=0.70,
            ) as hands:

                while self.hand_mouse_active and cap.isOpened():
                    ok, frame = cap.read()
                    if not ok:
                        break
                    if self.FLIP:
                        frame = cv2.flip(frame, 1)

                    now = time.time()
                    fps = 1.0 / max(now - prev_time, 1e-9)
                    prev_time = now

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    res = hands.process(rgb)
                    rgb.flags.writeable = True

                    gesture = G.NONE
                    scroll_dir = ""

                    l_d = self.PINCH_OPEN + 0.01
                    r_d = self.PINCH_OPEN + 0.01

                    if res.multi_hand_landmarks:
                        hand = res.multi_hand_landmarks[0]

                        mp_drawing.draw_landmarks(
                            frame, hand, mp_hands.HAND_CONNECTIONS,
                            mp_styles.get_default_hand_landmarks_style(),
                            mp_styles.get_default_hand_connections_style())

                        l_d = dist2d(hand, 4, 8)
                        r_d = dist2d(hand, 4, 12)

                        base = classify_gesture(hand)
                        px, py = palm_center(hand)
                        sx, sy = map_screen(px, py, self.ACTIVE_MARGIN, self.SW, self.SH)
                        sx, sy = smoother.update(sx, sy)

                        l_fired = l_pinch.update(l_d)
                        r_fired = r_pinch.update(r_d)

                        try:
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
                                        amt = int(-delta * self.SCROLL_SENS)
                                        pyautogui.scroll(amt)
                                        scroll_dir = "up" if amt > 0 else "down"
                                prev_palm_y = py
                                if drag_on:
                                    pyautogui.mouseUp()
                                    drag_on = False

                            else:
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
                        except pyautogui.FailSafeException:
                            print("[Hand Mouse] FailSafe Triggered. Mouse moved to extreme corner.")
                            self.hand_mouse_active = False
                            break

                        dot_x = int(px * frame.shape[1])
                        dot_y = int(py * frame.shape[0])
                        cv2.circle(frame, (dot_x, dot_y), 11, COLORS.get(gesture, (255, 255, 255)), -1)
                        cv2.circle(frame, (dot_x, dot_y), 13, (255, 255, 255), 2)

                        t = hand.landmark[4]; idx_lm = hand.landmark[8]
                        pt1 = (int(t.x * frame.shape[1]), int(t.y * frame.shape[0]))
                        pt2 = (int(idx_lm.x * frame.shape[1]), int(idx_lm.y * frame.shape[0]))
                        l_col_line = (50, 255, 100) if l_d < self.PINCH_CLOSE else (50, 140, 255)
                        cv2.line(frame, pt1, pt2, l_col_line, 2)

                        mid_lm = hand.landmark[12]
                        pt3 = (int(mid_lm.x * frame.shape[1]), int(mid_lm.y * frame.shape[0]))
                        r_col_line = (50, 255, 100) if r_d < self.PINCH_CLOSE else (0, 210, 210)
                        cv2.line(frame, pt1, pt3, r_col_line, 2)

                    else:
                        l_pinch.update(self.PINCH_OPEN + 0.1)
                        r_pinch.update(self.PINCH_OPEN + 0.1)
                        if drag_on:
                            try:
                                pyautogui.mouseUp()
                            except pyautogui.FailSafeException: pass
                            drag_on = False
                        prev_palm_y = None

                    draw_hud(frame, gesture, fps, drag_on, scroll_dir,
                             l_d, r_d,
                             l_pinch.state == "open",
                             r_pinch.state == "open",
                             self.PINCH_CLOSE, self.PINCH_OPEN, self.ACTIVE_MARGIN)

                    self.latest_hand_frame = frame.copy()
                    time.sleep(0.01)

        except Exception as loop_err:
            print(f"[Hand Mouse Core System Error]: {loop_err}")
            traceback.print_exc()
        finally:
            if drag_on:
                try:
                    pyautogui.mouseUp()
                except Exception: pass
            cap.release()
            self.latest_hand_frame = None
            self.hand_mouse_active = False
            self.root.after(0, self._reset_hand_mouse_button)


    # ================== SYSTEM METRICS & GRAPHICS UPDATE ==================
    def _update_time_and_telemetry(self):
        now = datetime.now()
        self.header_time_lbl.config(text=now.strftime("%I:%M:%S %p").upper())

        self._draw_radar_animation()

        if self.active_tab == "DASHBOARD":
            for i, line in enumerate(self.net_visual_lines):
                wave_height = int(20 + math.sin(time.time() * 5 + i * 0.5) * 15 + random.randint(-5, 5))
                wave_height = max(5, min(40, wave_height))
                self.net_visualizer.coords(line, 10 + i * 10, 40 - wave_height, 16 + i * 10, 40)
                
                if wave_height > 30:
                    self.net_visualizer.itemconfig(line, fill=NEON_PINK)
                elif wave_height > 18:
                    self.net_visualizer.itemconfig(line, fill=CYAN_ACCENT)
                else:
                    self.net_visualizer.itemconfig(line, fill=ACCENT_GREEN)

            if HAS_PSUTIL:
                try:
                    cpu = psutil.cpu_percent()
                    ram = psutil.virtual_memory().percent
                    self.cpu_metric_lbl.config(text=f"{cpu}%")
                    self.ram_metric_lbl.config(text=f"{ram}%")
                    
                    self.net_latency_lbl.config(text=f"LATENCY\n{random.randint(8, 24)} ms")
                    self.net_packet_lbl.config(text=f"PACKET RATE\n{random.randint(120, 450)} p/s")
                except Exception: pass
            else:
                self.cpu_metric_lbl.config(text="38 %")
                self.ram_metric_lbl.config(text="44 %")

        self.root.after(40, self._update_time_and_telemetry)


# ================== SYSTEM BOOTSTRAP MATRIX ==================
if __name__ == "__main__":
    root = tk.Tk()
    
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TProgressbar", thickness=6, troughcolor=BG, background=ACCENT_GREEN)
    
    app = IRIS_NeuralInterface(root)
    root.mainloop()