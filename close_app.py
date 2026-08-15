import os

def close_app(command):
    command = command.lower()

    if command.startswith("close "):
        app_name = command.replace("close ", "").strip()

        # common app mapping (Windows process names)
        app_map = {
            "tiktok": "TikTok.exe",
            "chrome": "chrome.exe",
            "notepad": "notepad.exe",
            "telegram": "Telegram.exe",
            "whatsapp": "WhatsApp.exe",
            "spotify": "Spotify.exe",
            "discord": "Discord.exe",
            "instagram": "Instagram.exe"
        }

        if app_name in app_map:
            process = app_map[app_name]
            os.system(f"taskkill /F /IM {process}")
            print(f"{app_name} closed successfully")
        else:
            print(f"{app_name} app not found in map")

    else:
        print("Invalid command")