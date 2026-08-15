import requests
from api import SERPER_API_KEY

#SERPER_API_KEY = "cd9d2687617267f893bf4064e627a5f2c5d0b094"

def serper_answer(query: str) -> str:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"q": query, "num": 1}

    try:
        # requests.post lai loop ma smoothly chalauna thau ma rakhne
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            answer_box = data.get("answerBox", {})
            answer = answer_box.get("answer") or answer_box.get("snippet")
            if answer: return answer
            
            organic = data.get("organic", [])
            if organic: return organic[0].get("snippet")
        return "माफ गर्नुहोला, मैले यसको उत्तर भेट्टाउन सकिन।"
    except Exception as e:
        return f"Error: {e}"


