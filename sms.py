import webbrowser
import time
import pyautogui

CLICK_X = 887
CLICK_Y = 665

facebook_contacts = {
    "lokesh": "https://www.messenger.com/e2ee/t/1200656701925364/",
    "group": "https://www.messenger.com/t/1565104188004424/",
    "vojaraj": "https://www.facebook.com/vojaraj.joshi",
    "khem": "https://www.facebook.com/khem.joshi"
}


def send_whatsapp_message(name, message):
    print(f"\n[*] System को WhatsApp खोल्दैछु र '{name}' लाई म्यासेज पठाउँदैछु...")
    
    # १. Windows Search बाट WhatsApp खोल्ने
    pyautogui.press('win')
    time.sleep(1)
    pyautogui.typewrite('whatsapp', interval=0.1)
    time.sleep(1)
    pyautogui.press('enter')
    
    # एप खुल्न ८ सेकेन्ड पर्खिने (कम्प्युटर स्लो छ भने यो १०-१२ बनाउनुहोला)
    time.sleep(8) 

    # २. Search (Ctrl + F) गर्ने
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1)

    # ३. साथीको नाम टाइप गर्ने
    pyautogui.typewrite(name, interval=0.1)
    time.sleep(3) # नाम सर्च भएर आउन पर्खिने

    # ४. पहिलो व्यक्ति छान्न Down Arrow थिचेर Enter गर्ने
    pyautogui.press('down')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(2) 

    # ५. म्यासेज टाइप गरेर पठाउने
    pyautogui.typewrite(message, interval=0.04)
    pyautogui.press('enter')
    print("[+] WhatsApp म्यासेज सफलतापूर्वक पठाइयो!\n")



def send_facebook_message(name, message):
    url = facebook_contacts[name]
    webbrowser.open(url)
    time.sleep(12)

    pyautogui.click(CLICK_X, CLICK_Y)
    time.sleep(1)

    pyautogui.typewrite(message, interval=0.04)
    pyautogui.press("enter")


# ===== PHOTO FROM CLIPBOARD =====
def send_whatsapp_photo(name):
    print(f"\n[*] System को WhatsApp खोल्दैछु र '{name}' लाई म्यासेज पठाउँदैछु...")
    
    # १. Windows Search बाट WhatsApp खोल्ने
    pyautogui.press('win')
    time.sleep(1)
    pyautogui.typewrite('whatsapp', interval=0.1)
    time.sleep(1)
    pyautogui.press('enter')
    
    # एप खुल्न ८ सेकेन्ड पर्खिने (कम्प्युटर स्लो छ भने यो १०-१२ बनाउनुहोला)
    time.sleep(8) 

    # २. Search (Ctrl + F) गर्ने
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1)

    # ३. साथीको नाम टाइप गर्ने
    pyautogui.typewrite(name, interval=0.1)
    time.sleep(3) # नाम सर्च भएर आउन पर्खिने
    # ४. पहिलो व्यक्ति छान्न Down Arrow थिचेर Enter गर्ने
    pyautogui.press('down')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(2) 

    # ५. म्यासेज टाइप गरेर पठाउने
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(2)
    
    pyautogui.press('enter')


def send_facebook_photo(name):
    url = facebook_contacts[name]
    webbrowser.open(url)
    time.sleep(12)

    pyautogui.click(CLICK_X, CLICK_Y)
    time.sleep(1)

    pyautogui.hotkey("ctrl", "v")
    time.sleep(2)

    pyautogui.press("enter")


    
    