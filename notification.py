import os
import sys
from plyer import notification
from playsound import playsound
import threading

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def play_sound():
    sound_file = resource_path(os.path.join("sound", "dipu.mp3"))
    if not os.path.exists(sound_file):
        print(f"Sound file not found: {sound_file}")
        return
    playsound(sound_file)


def show_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Dipu AI",
            timeout=5
        )
    except Exception as e:
        print("Notification Error:", e)
   
        