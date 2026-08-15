import os

from groq import Groq
from prompt import SYSTEM_PROMPT
from api import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


chat_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

def ai_response(user_input):
    global chat_history
    chat_history.append({"role": "user", "content": user_input})

    
    try:
        llm = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=chat_history,
            temperature=0.7,
            max_tokens=500
        )
        ai_answer = llm.choices[0].message.content
        chat_history.append({"role": "assistant", "content": ai_answer})
        if len(chat_history) > 20:
            chat_history = [chat_history[0]] + chat_history[-10:]
        return ai_answer
    except Exception as e:
        return f"Error: {str(e)}"

