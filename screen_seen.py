import base64
import os
from groq import Groq
import pyautogui
from dotenv import load_dotenv

from api import GROQ_API_KEY
client = Groq(api_key=GROQ_API_KEY)


# ======================
# MEMORY (HISTORY)
# ======================

chat_history = []

# ======================
# ENCODE IMAGE
# ======================
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# ======================
# SCREEN ANALYSIS WITH MEMORY
# ======================
def get_screen_analysis():
    global chat_history

    image_path = "dipu.jpg"
    pyautogui.screenshot(image_path)

    try:
        base64_image = encode_image(image_path)

        # Add user message with image
        chat_history.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "What is on my screen right now? Explain like a sweet assistant in 2 short sentences."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                },
            ],
        })

        # Send full history
        chat_completion = client.chat.completions.create(
            messages=chat_history,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )

        result = chat_completion.choices[0].message.content

        # Add AI response to history
        chat_history.append({
            "role": "assistant",
            "content": result
        })

        # OPTIONAL: limit history (very important ⚠️)
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        # Clean up image
        if os.path.exists(image_path):
            os.remove(image_path)

        return result

    except Exception as e:
        print(f"Error in Vision: {e}")
        return "Sorry baby, I am having trouble using the vision model right now."
    
    
    