# exam.py

import asyncio
import os
import webbrowser
import threading
import time
from datetime import datetime
from taxt_to_speak import speak
from config import exam_date as EXAM_DATE, exam_time as EXAM_TIME
# ─────────────────────────────────────────────
#  EXAM INFO
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  DATE CHECK FUNCTION
# ─────────────────────────────────────────────
def is_exam_near():
    today = datetime.now().date()
    exam_day = datetime.strptime(EXAM_DATE, "%Y-%m-%d").date()

    days_left = (exam_day - today).days

    return days_left <= 7   # 🔥 only last 7 days

# ─────────────────────────────────────────────
#  CLOSE APPS
# ─────────────────────────────────────────────
def close_all_browsers():
    os.system("taskkill /f /im chrome.exe")
    os.system("taskkill /f /im msedge.exe")

# ─────────────────────────────────────────────
#  OPEN MODEL PAPER
# ─────────────────────────────────────────────
def open_model_paper():
    webbrowser.open("https://www.google.com/search?q=class+10+model+paper")

# ─────────────────────────────────────────────
#  MAIN LOGIC
# ─────────────────────────────────────────────
def handle_exam_query(user_text):
    user_text = user_text.lower()

    # exam info
    if "exam" in user_text:
        return f"सर 📚 तपाईंको परीक्षा {EXAM_DATE} मा {EXAM_TIME} बाट सुरु हुन्छ।"

    # 🔥 ONLY activate if exam near
    if is_exam_near():

        if "open" in user_text or "youtube" in user_text or "tiktok" in user_text:
            close_all_browsers()
            open_model_paper()
            return "सर 😡 परीक्षा छ! अब कुनै पनि एप खोल्न पाइँदैन। पढाइमा ध्यान दिनुहोस्!"

        return "सर 😠 परीक्षा नजिकै छ! समय खेर नफाल्नुहोस्, पढ्नुहोस्!"

    return None

# ─────────────────────────────────────────────
#  REMINDER SYSTEM
# ─────────────────────────────────────────────
def start_exam_reminder(speak_func=None):
    def loop():
        while True:
            time.sleep(30)

            if is_exam_near():
                msg = "सर ⏰ परीक्षा नजिकै छ! के गर्दै हुनुहुन्छ? पढ्नुहोस्!"

                if speak_func:
                    asyncio.run(speak(msg))
                else:
                    print(msg)

    threading.Thread(target=loop, daemon=True).start()
