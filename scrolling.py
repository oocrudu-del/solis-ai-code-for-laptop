
#========scroll functions=======
import pyautogui


def scroll_up():
    pyautogui.press('up', presses=5)
def scroll_down():
    pyautogui.press('down', presses=5)
def scroll_to_top():
    pyautogui.hotkey('home')
def scroll_to_bottom():
    pyautogui.hotkey('end')
def perform_scroll_action(text):
    text = text.lower()
    if "scroll up" in text or "upar scroll karo" in text:
        scroll_up()
        return "Scrolling up"
    elif "scroll down" in text or "neeche scroll karo" in text:
        scroll_down()
        return "Scrolling down"
    elif "scroll to top" in text or "shuruat par jao" in text:
        scroll_to_top()
        return "Going to top"
    elif "scroll to bottom" in text or "ant par jao" in text:
        scroll_to_bottom()
        return "Going to bottom"
    return None
