
import asyncio

from taxt_to_speak import speak
import ctypes
import time

# ─────────────────────────────────────────────
#  SECURITY DATA
# ─────────────────────────────────────────────
OWNER_NAME = "khem"
PASSWORD = "2066"

# trigger words (danger)
DANGER_WORDS = [
    "code bigarxu",
    "code delete",
    "file delete",
    "ai delete",
    "system delete",
    "hack garxu"
]

# ─────────────────────────────────────────────
#  LOCK SYSTEM
# ─────────────────────────────────────────────
def lock_pc():
    ctypes.windll.user32.LockWorkStation()

# ─────────────────────────────────────────────
#  CHECK SECURITY
# ─────────────────────────────────────────────
def handle_security(user_text, speak_func=None, get_input_func=None):
    text = user_text.lower()

    # check danger words
    if any(word in text for word in DANGER_WORDS):

        msg = "⚠️ तपाईं को हुनुहुन्छ? आफ्नो नाम भन्नुहोस्!"
        if speak_func:
              asyncio.run(speak(msg))
        else:
            print(msg)

        # get name
        name = get_input_func() if get_input_func else input("Name: ")

        if name.lower() == OWNER_NAME:

            msg = "पासवर्ड भन्नुहोस्!"
            if speak_func:
               asyncio.run(speak(msg))
            else:
                print(msg)

            pwd = get_input_func() if get_input_func else input("Password: ")

            if pwd == PASSWORD:
                ok = "✅ Access Granted"
                if speak_func:
                    asyncio.run(speak(ok))
                else:
                    print(ok)
                return None
            else:
                fail = "❌ गलत पासवर्ड! सिस्टम लक हुँदैछ..."
        else:
            fail = "❌ गलत व्यक्ति! सिस्टम लक हुँदैछ..."

        if speak_func:
            asyncio.run(speak(fail))
        else:
            print(fail)

        time.sleep(1)
        lock_pc()

        return "LOCKED"

    return None