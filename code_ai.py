import os
import tkinter as tk
from tkinter import scrolledtext
import pyperclip
import webbrowser
from groq import Groq
from dotenv import load_dotenv
from api import GROQ_API_KEY

# Load API
load_dotenv()
client = Groq(api_key=GROQ_API_KEY)

# =========================
# MEMORY (HISTORY)
# =========================
chat_history = []

# =========================
# UI BOX FUNCTION
# =========================
def show_code_ui(code_text, filename):
    # सानो विन्डो बनाउने
    root = tk.Tk()
    root.title("🤖 AI Generated Code")
    root.geometry("450x450") # सानो बक्स
    root.configure(bg="#1e1e1e", padx=10, pady=10)
    root.attributes("-topmost", True) # यो बक्स सधैं अगाडि आउँछ

    # Code देखाउने ठाउँ
    text_area = scrolledtext.ScrolledText(root, font=("Consolas", 11), bg="#000000", fg="#00ff00", insertbackground="white")
    text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    text_area.insert(tk.END, code_text)

    # Button राख्ने फ्रेम
    btn_frame = tk.Frame(root, bg="#1e1e1e")
    btn_frame.pack(fill=tk.X)

    # Copy गर्ने फङ्सन
    def copy_code():
        pyperclip.copy(text_area.get("1.0", tk.END).strip())
        btn_copy.config(text="✅ Copied!")
        root.after(2000, lambda: btn_copy.config(text="📋 Copy Code"))

    # Run गर्ने फङ्सन (Chrome मा खोल्ने)
    def run_code():
        filepath = os.path.abspath(filename)
        webbrowser.open(f"file://{filepath}")

    # Buttons
    btn_copy = tk.Button(btn_frame, text="📋 Copy Code", command=copy_code, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
    btn_copy.pack(side=tk.LEFT, padx=5)

    btn_run = tk.Button(btn_frame, text="🌐 Run in Chrome", command=run_code, bg="#FF9800", fg="white", font=("Arial", 10, "bold"))
    btn_run.pack(side=tk.LEFT, padx=5)

    root.mainloop()

# =========================
# AI CODER WITH MEMORY
# =========================
def smart_ai_coder(prompt=None):
    global chat_history

    if not prompt:
        print("❌ कुनै कमान्ड दिइएको छैन!")
        return None

    print(f"🗣️ Command Received: {prompt}")
    print("🤖 AI ले कोड तयार पार्दैछ...")

    try:
        # Add user prompt to history
        chat_history.append({
            "role": "user",
            "content": prompt
        })

        # AI request with full history
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b", # मैले Groq को Fast मोडल राखेको छु
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write ONLY pure code. No markdown backticks like ```html. "
                        "First line must be comment showing language like: "
                        "# language: python or <!-- language: html -->"
                    )
                }
            ] + chat_history
        )

        full_response = completion.choices[0].message.content.strip()

        # Remove markdown backticks if AI adds them
        if full_response.startswith("```"):
            full_response = "\n".join(full_response.split("\n")[1:-1])

        # Save AI response to history
        chat_history.append({
            "role": "assistant",
            "content": full_response
        })

        # Limit History
        if len(chat_history) > 12:
            chat_history = chat_history[-12:]

        # Detect file type
        lower = full_response.lower()
        if "html" in lower[:100]:
            filename = "code/index.html"
        elif "javascript" in lower[:100] or "js" in lower[:100]:
            filename = "code/app.js"
        elif "css" in lower[:100]:
            filename = "code/style.css"
        else:
            filename = "code/python.py"

        # folder create
        os.makedirs("code", exist_ok=True)

        # save file
        with open(filename, "w", encoding="utf-8") as f:
            f.write(full_response)

        print(f"✅ Code ready and saved to: {filename}")

        # यहाँबाट मात्र UI Box खुल्छ
        show_code_ui(full_response, filename)

        return filename

    except Exception as e:
        print("❌ AI Code Error:", e)
        return None
    
    
if __name__ == "__main__":
    while True:
        user_input = input("Enter your coding command (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        smart_ai_coder(user_input)

