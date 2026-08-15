import cv2
import time
import json
import os
import datetime
import threading
import base64
import requests
from dotenv import load_dotenv
from ai_core import ai_response
from api import GEMINI_API_KEY, GROQ_API_KEY
from groq import Groq
# तपाईंको Config र Prompt इम्पोर्ट

from prompt import SYSTEM_PROMPT, prompt


API_KEY = GEMINI_API_KEY
client = Groq(api_key=GROQ_API_KEY)
#==========================================
# 0. GEMINI API SETUP
#==========================================
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
HEADERS = {"Content-Type": "application/json"}
JSON_FILE = "data.json"
IMAGE_FILE = "photo.png"
is_running = True

#==========================================
# 1. VISION AGENT (क्यामेराको काम गर्ने भाग)
#==========================================
def save_to_json(ai_answer):
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
    else:
        data = []
        
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data.append({"timestamp": current_time, "ai_response": ai_answer})
    
    # ५ वटा मात्र राख्ने नियम हटाएर ५० वटा सम्म राख्ने बनाइयो (लगातार चल्नको लागि)
    data = data[-100:] 

    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)

def ask_vision_ai(image_path):
    with open(image_path, "rb") as image_file:
        image_b64 = base64.b64encode(image_file.read()).decode("utf-8")
        
    # क्यामेरा एआईको लागि विषेश कडा निर्देशन (यसले हातको सामान र अनुहारको डिटेल दिन्छ)
    ENHANCED_VISION_PROMPT = f"""
    {prompt}
    [CRITICAL INSTRUCTION FOR VISION AI]:
    Analyze the image in EXTREME DETAIL. You MUST include:
    1. The person's physical appearance, clothing color/type, and exact facial expression (happy, sad, neutral).
    2. EXACTLY what objects are visible, especially WHAT IS IN THEIR HANDS (e.g., phone, cup, pen, nothing).
    3. The background and environment.
    Provide a highly descriptive summary so a text AI can answer questions about the user's looks and objects accurately.
    """

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct", 
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": ENHANCED_VISION_PROMPT}, 
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }]
    )
    return response.choices[0].message.content

def vision_worker():
    global is_running
    cap = cv2.VideoCapture(0)
    
    while is_running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(2)
            continue
        
        cv2.imwrite(IMAGE_FILE, frame)
        try:
            result = ask_vision_ai(IMAGE_FILE)
            save_to_json(result)
        except Exception as e:
            print(f"\n[Background Vision Error]: {str(e)}\n")
            
        if os.path.exists(IMAGE_FILE):
            os.remove(IMAGE_FILE)
            
        # १० सेकेन्डको सट्टा ५ सेकेन्ड पर्खिने बनाइयो (छिटो रेस्पोन्सको लागि)
        for _ in range(5):
            if not is_running:
                break
            time.sleep(1)

    cap.release()

#==========================================
# 2. CHAT AGENT (च्याट गर्ने भाग)
#==========================================
def get_camera_context():
    if not os.path.exists(JSON_FILE):
        return "NO_DATA: The camera is still capturing or initializing."
    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
        if not data:
            return "NO_DATA: Camera data is currently empty."
        
        # पछिल्लो ३ वटा (अझै धेरै) डिटेल लिने
        recent_logs = data[-3:]
        context = ""
        for log in recent_logs:
            context += f"- {log['ai_response']}\n"
        return context
    except:
        return "NO_DATA: Error reading camera data."

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def get_ai_response(user_input):
    global chat_history
    camera_data = get_camera_context()

    SMART_INSTRUCTIONS = f"""
    {SYSTEM_PROMPT}
    [CURRENT VISUAL CONTEXT FROM CAMERA]:
    {camera_data}
    
    [CRITICAL BEHAVIOR RULES]:
    You are an active, highly empathetic personal AI assistant.
    VISUAL QUESTIONS: If the user asks "How do I look?", "What is in my hand?", or about their surroundings, READ THE [CURRENT VISUAL CONTEXT] and answer accurately based ONLY on that.
    NO DATA HANDLING: If the visual context says "NO_DATA", DO NOT stay blank. Reply politely: "बोस, मेरो क्यामेरा खुल्दै छ, एकैछिन पर्खिनुहोस् ल!".
    EMOTION: If the context says the user looks sad, ask: "के भयो बोस, किन दुखी हुनुहुन्छ?".
    LANGUAGE: Always respond in the language the user is speaking.
    """
    
    chat_history[0]["content"] = SMART_INSTRUCTIONS
    chat_history.append({"role": "user", "content": user_input})
    
    gemini_contents = []
    for msg in chat_history[1:]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
        
    payload = {
        "system_instruction": {
            "parts": [{"text": SMART_INSTRUCTIONS}]
        },
        "contents": gemini_contents
    }
    
    try:
        response = requests.post(GEMINI_URL, headers=HEADERS, data=json.dumps(payload))
        response_data = response.json()
        
        if response.status_code == 200:
            ai_answer = response_data['candidates'][0]['content']['parts'][0]['text']
        else:
            ai_answer = ai_response(user_input)  # फेल भएमा पुरानो AI प्रयोग गर्ने

        if not ai_answer or ai_answer.strip() == "":
            ai_answer = "माफ गर्नुहोला बोस, मैले ठ्याक्कै बुझ्न सकिनँ। फेरि भन्नुहुन्छ कि?"

        chat_history.append({"role": "assistant", "content": ai_answer})
        
        # History Limit (२० वटा सम्म म्यासेज याद राख्ने)
        if len(chat_history) > 20:
            chat_history = [chat_history[0]] + chat_history[-10:]
            
        return ai_answer
    except Exception as e:
        chat_history.pop()  
        return f"Error: {str(e)}"

#==========================================
# 3. MAIN RUNNER
#==========================================
