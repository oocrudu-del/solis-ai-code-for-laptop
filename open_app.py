import pyautogui
import pygetwindow as gw
import time
import webbrowser
import re

class AppLauncher:
    def __init__(self):
        # Screen size setup
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Predefined websites
        self.websites = {
            "facebook": "https://www.facebook.com",
            "tiktok": "https://www.tiktok.com",
            "instagram": "https://www.instagram.com",
            "youtube": "https://www.youtube.com",
            "chatgpt": "https://chat.openai.com",
            "google": "https://www.google.com",
            "whatsapp": "https://web.whatsapp.com"
        }

    def _open_logic(self, app_name):
        """Paila website ho ki haina check garchha, chaina bhane Windows search garchha."""
        app_name = app_name.strip().lower()
        if app_name in self.websites:
            print(f"Opening {app_name} in Browser...")
            webbrowser.open(self.websites[app_name])
            return True # Web browser ho
        else:
            print(f"Searching and opening {app_name} locally...")
            pyautogui.press("win")
            time.sleep(0.5)
            pyautogui.write(app_name, interval=0.1)
            time.sleep(0.7)
            pyautogui.press("enter")
            return False # Local app ho

    def _move_window(self, app_name, position):
        """Window lai correctly resize ra move garchha."""
        time.sleep(2.5) # App khulna dine samaya
        
        target_win = None
        start_search = time.time()
        
        # 5 second samma window search garne
        while time.time() - start_search < 5:
            all_wins = gw.getWindowsWithTitle('')
            for w in all_wins:
                if app_name.lower() in w.title.lower():
                    target_win = w
                    break
            if target_win: break
            time.sleep(0.5)

        if not target_win:
            target_win = gw.getActiveWindow()

        try:
            if target_win:
                if position == "left":
                    target_win.restore()
                    target_win.moveTo(0, 0)
                    target_win.resizeTo(self.screen_width // 2, self.screen_height)
                elif position == "right":
                    target_win.restore()
                    target_win.moveTo(self.screen_width // 2, 0)
                    target_win.resizeTo(self.screen_width // 2, self.screen_height)
                elif position == "fullscreen":
                    target_win.maximize()
                print(f"Moved {app_name} to {position}")
        except Exception as e:
            print(f"Window move error: {e}")

    def process_command(self, request):
        """Main method jaslai loop bata call garne."""
        request = request.lower()
        
        if not any(word in request for word in ["open", "khola", "khol"]):
            return "Kripaya 'open' command prayog garnuhos."

        # Cleaning command
        clean_text = re.sub(r'\b(open|khola|khol)\b', '', request).strip()
        
        # Split by 'and', 'ra', 'aani', ','
        delimiters = r"and|ra|aani|,"
        parts = re.split(delimiters, clean_text)

        results = []
        for part in parts:
            part = part.strip()
            if not part: continue

            # Detect position
            position = "fullscreen"
            if "left" in part or "lift" in part:
                position = "left"
                part = part.replace("left", "").replace("lift", "").strip()
            elif "right" in part:
                position = "right"
                part = part.replace("right", "").strip()

            # Execute
            is_web = self._open_logic(part)
            if not is_web:
                self._move_window(part, position)
            
            results.append(f"{part}({position})")

        return f"Successfully processed: {', '.join(results)}"