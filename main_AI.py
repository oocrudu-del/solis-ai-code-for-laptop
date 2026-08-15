from code_ai import smart_ai_coder
from screen_seen import get_screen_analysis
import threading
from google_ai import  vision_worker,  get_ai_response
from weather import show_weather
from ai_core import ai_response

# यो फाइल तिम्रो Voice Loop फाइलमा Import हुने बित्तिकै Camera Background मा आफै Start हुन्छ।
print("[SYSTEM] Background Camera Agent Started...")
vision_thread = threading.Thread(target=vision_worker, daemon=True)
vision_thread.start()

def extract_city(command):
    """
    Command बाट city निकाल्ने function
    Example:
    'tell me weather from nepal'
    -> 'nepal'
    """

    command = command.lower()

    # common keywords remove
    words_to_remove = [
        "tell", "me", "weather", "from", "in", "at", "lat", "long",
        "in", "of", "what", "is",
        "the", "today", "temperature","show", "like", "for"
    ]

    words = command.split()

    city_words = [word for word in words if word not in words_to_remove]

    return " ".join(city_words)


def controller(command):
    # कमाण्डलाई सानो अक्षर (lowercase) मा बदल्ने
    command_lower = command.lower()

    # यदि युजरले Screen को कुरा गर्यो भने
    if "screen" in command_lower:
        return get_screen_analysis()

    # यदि युजरले Code को कुरा गर्यो भने
    elif "code" in command_lower or "coding" in command_lower:
        return smart_ai_coder(command)
    elif "weather" in command_lower:
    
        city_name = extract_city(command_lower)

        # default city
        if not city_name:
            city_name = "Kathmandu"

        return show_weather(city_name)
    # यदि कमाण्डमा screen वा code छैन भने (Normal कुरा वा Camera को कुरा)
    else:
        return get_ai_response(command)


