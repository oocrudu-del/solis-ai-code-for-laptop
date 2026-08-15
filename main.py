import os
import re
import pygame
import requests as web_requests  # 'requests' लिस्टसँग नाम नजुधोस् भन्नका लागि Rename गरिएको
import webbrowser
import time
import datetime
import wikipedia
import asyncio
import random
import pyautogui
import speech_recognition as sr
from notification import show_notification
from search import serper_answer
from sms import (
    send_whatsapp_message,
    send_facebook_message,
    send_whatsapp_photo,
    send_facebook_photo,
    facebook_contacts
)
from youtube_player import play_music_on_youtube, play_random_nepali_song, play_sad_song
from image import generate_image_dipu   
from scrolling import scroll_up, scroll_down, perform_scroll_action
from taxt_to_speak import speak
from tast import VoiceRecognizer
from auto_file import create_file_desktop, search_file, open_file_location, delete_file, ai_command
from open_app import AppLauncher
from exam import handle_exam_query, start_exam_reminder, is_exam_near, close_all_browsers, open_model_paper, EXAM_DATE, EXAM_TIME
from security import handle_security, lock_pc
from close_app import close_app
from decision import classify_intent
import threading
import edge_tts
import tkinter as tk
from main_AI import controller


# ==========================================
# थपिएका नयाँ मोड्युलहरू (Voice & Decision)
# ==========================================

voice_recognizer = VoiceRecognizer()


# ==========================================
# बाँकी प्रणाली सेटअप
# ==========================================
show_notification("SOLIS AI", "SOLIS AI is now online and ready to assist you!")

API_KEY = "apf_kkc2ry3mijdcxvilbs6zicgm"
url = "https://apifreellm.com/api/v1/chat"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def split_commands(text):
    return re.split(r' and | then |,', text)


def run():
    print("SOLIS AI Started 🔥")
    asyncio.run(speak("Welcome back Sir, I am Solis AI Assistant, online now."))

    while True:
        try:
            # नयाँ VoiceRecognizer मार्फत कमाण्ड सुन्ने
            main_request = voice_recognizer.command()

            if not main_request:
                continue

            # कमाण्डहरू टुक्राउने (Split Commands)
            requests_list = split_commands(main_request)

            for request in requests_list:
                request = request.strip()

                if not request:
                    continue

                # नयाँ DecisionMaker मार्फत निर्णय लिने
                intent = classify_intent(request)

                print(f"Request: {request}")
                print(f"Intent: {intent}")
                
                if intent == "RELATIONSHIP":
                    if "jpt" in request:
                        asyncio.run(speak("Let me check, please wait...")) 
                        data = {
                            "message": f"Give a very short answer: {request}",
                            "max_tokens": 300
                        }
                        
                        # web_requests प्रयोग गरेर API कल गर्ने
                        r = web_requests.post(url, headers=headers, json=data)
                        res = r.json()
                        asyncio.run(speak(res.get("response", "No response received.")))
                        continue    
                    
                    if "weather" in request or "news" in request or "who" in request:
                        result = serper_answer(request)
                        asyncio.run(speak(result))
                        continue
               
                elif intent == "IMAGE":
                    if "create" in request or "image" in request or "photo" in request:
                        prompt = request.replace("create", "").replace("image", "").replace("make", "").strip()
                        msg = generate_image_dipu(prompt)
                        asyncio.run(speak(msg))
                        continue
          
                elif intent == "SYSTEM":
                    reply = perform_scroll_action(request)
                    if reply:
                        asyncio.run(speak(reply))
                    
                    file = ai_command(request)
                    if file:
                        asyncio.run(speak(file))
                        
                    # 🔐 SECURITY CHECK FIRST
                    sec = handle_security(request, speak)
                    if sec == "LOCKED":
                        continue
                                            
                    if "play nepali song" in request:
                        play_random_nepali_song()
                        continue
                    elif "ghau lagyo" in request or "malai ghau" in request:
                        print("DIPU: 💔 Timilai ghau lagyo jasto cha... sad song bajauchu")
                        asyncio.run(speak("Timilai ghau lagyo jasto cha, sad song bajauchu"))
                        play_sad_song()
                        continue
                    elif "play" in request or "music" in request:
                        song = request.replace("play", "").replace("music", "").strip()
                        asyncio.run(speak(f"Playing {song}"))
                        play_music_on_youtube(song)
                        continue
                    
                    response = handle_exam_query(request)
                    if response:
                        asyncio.run(speak(response))
                        continue   
                        
                    if "open" in request or "khola" in request:
                        asyncio.run(speak(controller(request)))
                        app_launcher = AppLauncher()
                        app_launcher.process_command(request)
                        
                        continue
                
                    close = close_app(request)
                    if close:
                        asyncio.run(speak(close))
                        
                    elif "close" in request or "band" in request:
                        pyautogui.hotkey("alt", "f4")
                        asyncio.run(speak(controller(request)))    
         
                    elif "minimise" in request or "desktop" in request or "sab data hide" in request or "sab data minimize" in request:
                        pyautogui.hotkey("super", "d")
                        asyncio.run(speak("all Applications minimized"))
                        continue
                    elif "delete all" in request or "clear all" in request or "sab data delete" in request:
                        pyautogui.hotkey("ctrl", "a")
                        time.sleep(1)
                        pyautogui.press("delete")
                        pyautogui.press("enter")
                        asyncio.run(speak("all data deleted"))
                        continue
                    elif "mute" in request or "volume mute" in request or "system mute" in request or "chhoppa" in request:
                        pyautogui.press("volumemute")
                        asyncio.run(speak("system muted"))

                    elif "volume up" in request or "volume badau" in request or "volume increase" in request or "volume thulo" in request:
                        pyautogui.press("volumeup")
                        asyncio.run(speak("volume increased"))
                        
                    elif "new desktop" in request or "virtual desktop" in request or "naya desktop" in request:
                        pyautogui.hotkey("win", "ctrl", "d")
                        asyncio.run(speak("new virtual desktop created"))
                        
                    elif "take a screenshot" in request or "screenshot le" in request or "screen capture" in request:
                        screenshot = pyautogui.screenshot()
                        screenshot.save("screen.png")
                        asyncio.run(speak("Screenshot taken and saved"))
                        continue

                    #======= SHUTDOWN, RESTART, LOGOUT ======
                    elif "shutdown" in request or "power off" in request or "system off" in request or "band gara" in request:
                        asyncio.run(speak("ok sir, system shutting down"))
                        os.system("shutdown /s /t 5")
                        break

                    elif "restart" in request or "system restart" in request or "punarjagaran" in request:
                        asyncio.run(speak("ok sir, system restarting"))
                        os.system("shutdown /r /t 5")
                        break
                        
                    elif "lock off" in request or "dipu sign out" in request or "logout" in request or "system logout" in request:
                        asyncio.run(speak("Logging off system"))
                        os.system("shutdown /l")
                        break

                    #====== WEB SEARCH ======
                    elif "search" in request:
                        query = request.replace("search", "").strip()
                        if query == "":
                            asyncio.run(speak("What should I search?"))
                            continue
                        asyncio.run(speak(f"Searching {query}"))
                        webbrowser.open(f"https://www.google.com/search?q={query}")
                        continue
                        
                    elif "search youtube" in request:
                        query = request.replace("search youtube", "").replace("youtube", "").strip()
                        asyncio.run(speak(f"Searching on YouTube {query}"))
                        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
                        continue

                    elif "show my house" in request:
                        webbrowser.open("https://www.google.com/maps/place//@28.6544687,81.0475076,19.25z")
                        asyncio.run(speak("Opening your location on Google Maps"))    
                        continue
                    
                    #====== TIME AND DATE ======
                    elif "time" in request:
                        now_time = datetime.datetime.now().strftime("%H:%M")
                        asyncio.run(speak("current time is " + now_time))

                    elif "date" in request:
                        now_date = datetime.datetime.now().strftime("%d:%m")
                        asyncio.run(speak("current date is " + now_date))

                    # ====== WIKIPEDIA SEARCH ======
                    elif "wikipedia" in request or " who is " in request or " what is " in request:
                        try:
                            asyncio.run(speak("Searching Wikipedia"))
                            query = request.replace("dipu wikipedia", "")
                            result = wikipedia.summary(query, sentences=5)
                            print("Wiki:", result)
                            asyncio.run(speak(result))
                        except wikipedia.exceptions.DisambiguationError:
                            asyncio.run(speak("This topic has multiple meanings, please be more specific"))
                        except wikipedia.exceptions.PageError:
                            asyncio.run(speak("No information found on Wikipedia"))

                    # ===== SEND WHATSAPP PHOTO =====
                    elif "send whatsapp photo to" in request or "photo send" in request:
                        contact_name = request.replace("send whatsapp photo to", "").strip()
                        msg_to_send = voice_recognizer.command()
                        asyncio.run(speak(f"Sending photo to {contact_name} on WhatsApp"))
                        send_whatsapp_message(contact_name, msg_to_send)
                        continue

                    # ===== SEND FACEBOOK PHOTO =====
                    elif "send facebook photo to" in request:
                        for name in facebook_contacts:
                            if name in request:
                                asyncio.run(speak(f"sending photo to {name} sir"))
                                send_facebook_photo(name)
                                asyncio.run(speak("photo sent"))
                                continue
                                
                    #======= SEND WHATSAPP MESSAGE ======
                    elif "send whatsapp message to" in request:
                        contact_name = request.replace("send whatsapp message to", "").strip()
                        asyncio.run(speak(f"what message do you want to send to {contact_name} sir"))
                        msg_to_send = voice_recognizer.command()
                        send_whatsapp_message(contact_name, msg_to_send)
                        continue
                    
                    elif "send facebook message to" in request:
                        names = request.replace("send facebook message to", "").strip()
                        name_list = names.split(",")
                        asyncio.run(speak("what is the message sir"))
                        message = voice_recognizer.command()
                                    
                        for name in name_list:
                            name = name.strip()
                            if name in facebook_contacts:
                                send_facebook_message(name, message)
                                asyncio.run(speak("your message is sent sir"))
                            else:
                                asyncio.run(speak(f"{name} not found in contacts"))
                        continue
                        
                    elif "bye" in request:
                        asyncio.run(speak("ok sir, have a nice day"))
                        break
                
                elif intent == "LLM":
                    response = controller(request)
                    asyncio.run(speak(response))
            
        except Exception as e:
            print(f"Sorry, I couldn't process that. Error: {e}")
            continue
        
        
if __name__ == "__main__":
    run()


