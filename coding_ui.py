import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyperclip
import webbrowser
import requests

from groq import Groq
from api import GEMINI_API_KEY, GROQ_API_KEY

# API configuration
API_KEY = GEMINI_API_KEY

try:
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
    else:
        groq_client = None
except Exception as e:
    groq_client = None
    print(f"Groq Init Error: {e}")

# Global Memory
chat_history = []
current_code_state = ""

# =========================
# AI Logic (Dual Engine Selection with Context & Explanation Structure)
# =========================
def generate_code_from_ai(prompt, provider="Gemini (1.5-Flash)", existing_code=""):
    global chat_history
    
    # AI लाई कोड र व्याख्या फरक-फरक ढाँचामा पठाउन निर्देश दिने प्रम्प्ट
    system_instruction = (
        "You are an expert AI software developer.\n"
        "Your task is to write high-quality code or modify existing code, AND provide a brief, clear explanation.\n"
        "You MUST split your response into two clear sections using [EXPLANATION] and [CODE] tags exactly as shown:\n\n"
        "[EXPLANATION]\n"
        "(Explain what the code does or what changes were made in a brief, friendly manner in simple English or Nepalese.)\n\n"
        "[CODE]\n"
        "(Write ONLY the raw updated source code here. Do not wrap code in markdown like ```html or ```python. "
        "The very first line of the code must be a comment specifying the language.)"
    )

    full_user_content = prompt
    if existing_code:
        full_user_content = (
            f"--- EXISTING CODE ---\n{existing_code}\n"
            f"--- USER INSTRUCTION ---\n{prompt}\n\n"
            f"Please update the existing code according to the instruction."
        )

    # १. प्रयोगकर्ताले Groq मोडल रोजेको खण्डमा
    if "Groq" in provider:
        if not GROQ_API_KEY or not groq_client:
            raise ValueError("Groq API Key फेला परेन वा कन्फिगर गरिएको छैन।")
        
        try:
            messages = [{"role": "system", "content": system_instruction}]
            for chat in chat_history[-6:]:
                messages.append(chat)
            messages.append({"role": "user", "content": full_user_content})

            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.2,
                timeout=12
            )
            ai_text = completion.choices[0].message.content.strip()
            return ai_text, "Groq"
        except Exception as groq_err:
            raise RuntimeError(f"Groq Engine Failed: {groq_err}")

    # २. प्रयोगकर्ताले Gemini मोडल रोजेको खण्डमा (वा डिफल्ट)
    else:
        try:
            if not GEMINI_API_KEY:
                raise ValueError("Gemini API Key missing.")
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"
            
            contents = []
            for chat in chat_history[-6:]:
                role = "model" if chat["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": chat["content"]}]
                })
            contents.append({"role": "user", "parts": [{"text": full_user_content}]})

            payload = {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.2}
            }

            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            
            if response.status_code == 200:
                resp_json = response.json()
                ai_text = resp_json['candidates'][0]['content']['parts'][0]['text'].strip()
                return ai_text, "Gemini"
            else:
                raise ValueError(f"Gemini API Status {response.status_code}")

        except Exception as gemini_err:
            raise RuntimeError(f"AI Engine failed.\nGemini: {gemini_err}")


# =========================
# UI Application
# =========================
class CoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ SOLIS CUT - Advanced AI Developer Studio")
        self.root.geometry("1150x750")
        self.root.configure(bg="#0f0f16") # Deep Dark Indigo/Violet space theme
        
        self.last_filename = ""
        self.file_list = []
        self.typing_job = None # Typewriter effect handle
        
        self.create_header()
        self.create_main_workspace()
        self.create_status_bar()

    def create_header(self):
        # Top Header Frame
        header_frame = tk.Frame(self.root, bg="#161625", height=60, bd=0, relief="flat")
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Logo Label with colorful modern color
        logo_label = tk.Label(
            header_frame, 
            text=" ⚡ SOLIS CUT AI ", 
            fg="#00e5ff",  # Cyber Neon Cyan
            bg="#161625", 
            font=("Segoe UI", 14, "bold")
        )
        logo_label.pack(side=tk.LEFT, padx=15, pady=12)

        subtitle_label = tk.Label(
            header_frame,
            text="| Interactive Studio",
            fg="#8c8ca3",
            bg="#161625",
            font=("Segoe UI", 10, "italic")
        )
        subtitle_label.pack(side=tk.LEFT, padx=2, pady=12)

        # Clear and New Session Button
        btn_new_chat = tk.Button(
            header_frame,
            text="🧹 Clear / New Chat",
            command=self.new_chat,
            bg="#ff0055", # Neon Rose/Pink
            fg="#ffffff",
            activebackground="#cc0044",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=12
        )
        btn_new_chat.pack(side=tk.RIGHT, padx=15, pady=12)

        # Dropdown Model Selector styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", 
                        fieldbackground="#202030", 
                        background="#161625", 
                        foreground="#ffffff", 
                        darkcolor="#161625", 
                        lightcolor="#161625",
                        bordercolor="#34344e")

        self.provider_var = tk.StringVar(value="Gemini (1.5-Flash)")
        provider_combo = ttk.Combobox(
            header_frame, 
            textvariable=self.provider_var, 
            values=["Gemini (1.5-Flash)", "Groq (Llama-3.3)"],
            state="readonly",
            width=22,
            style="TCombobox"
        )
        provider_combo.pack(side=tk.RIGHT, padx=15, pady=12)

        lbl_engine = tk.Label(
            header_frame, 
            text="🤖 Engine:", 
            fg="#a5a5cc", 
            bg="#161625", 
            font=("Segoe UI", 10, "bold")
        )
        lbl_engine.pack(side=tk.RIGHT, padx=2, pady=12)

    def create_main_workspace(self):
        # Paned Window layout
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#0f0f16", bd=0)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ====================
        # 1. Left Panel (Instructions & Chat History)
        # ====================
        left_frame = tk.Frame(self.main_pane, bg="#161625", width=360)
        self.main_pane.add(left_frame)

        lbl_chat = tk.Label(
            left_frame, 
            text="💬 CHAT & SYSTEM EXPLANATION", 
            fg="#a5a5cc", 
            bg="#161625", 
            font=("Segoe UI", 9, "bold")
        )
        lbl_chat.pack(anchor="w", padx=12, pady=(12, 6))

        # Chat display window
        self.chat_display = scrolledtext.ScrolledText(
            left_frame, 
            bg="#0f0f16", 
            fg="#e2e2ec", 
            insertbackground="white",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=1,
            highlightbackground="#26263b"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)
        self.chat_display.insert(tk.END, "🤖 AI: नमस्ते! मलाई कुनै पनि कामको निर्देश दिनुहोस्।\nतपाईँको निर्देशन अनुसारको विवरण यहाँ आउनेछ र कोड दायाँ पट्टी जेनेरेट हुनेछ।\n\n")
        self.chat_display.config(state=tk.DISABLED)

        # Prompt input box
        prompt_label = tk.Label(left_frame, text="Enter instruction / chat here:", fg="#a5a5cc", bg="#161625", font=("Segoe UI", 9))
        prompt_label.pack(anchor="w", padx=12, pady=(8, 2))

        self.prompt_entry = tk.Entry(
            left_frame, 
            bg="#202030", 
            fg="#ffffff", 
            insertbackground="white", 
            font=("Segoe UI", 11),
            bd=0,
            highlightthickness=1,
            highlightbackground="#34344e"
        )
        self.prompt_entry.pack(fill=tk.X, ipady=12, padx=12, pady=5)
        self.prompt_entry.bind("<Return>", lambda event: self.generate_code())

        # Action generate button
        self.btn_generate = tk.Button(
            left_frame, 
            text="🚀 Apply & Generate Code", 
            command=self.generate_code, 
            bg="#7c4dff", # Cyber Purple
            fg="white", 
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#651fff",
            activeforeground="white"
        )
        self.btn_generate.pack(fill=tk.X, padx=12, pady=(5, 12), ipady=8)

        # ====================
        # 2. Middle Panel (File Explorer Simulation)
        # ====================
        self.explorer_frame = tk.Frame(self.main_pane, bg="#11111a", width=160)
        self.main_pane.add(self.explorer_frame)

        lbl_explorer = tk.Label(
            self.explorer_frame, 
            text="📁 EXPLORER", 
            fg="#a5a5cc", 
            bg="#11111a", 
            font=("Segoe UI", 9, "bold")
        )
        lbl_explorer.pack(anchor="w", padx=10, pady=(12, 6))

        self.file_listbox = tk.Listbox(
            self.explorer_frame,
            bg="#11111a",
            fg="#cfcfdb",
            selectbackground="#202030",
            selectforeground="#00e5ff",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # ====================
        # 3. Right Panel (Code Workspace Editor)
        # ====================
        right_frame = tk.Frame(self.main_pane, bg="#0d0d14")
        self.main_pane.add(right_frame)

        # Tab bar
        self.tab_frame = tk.Frame(right_frame, bg="#0d0d14", height=35)
        self.tab_frame.pack(fill=tk.X, side=tk.TOP)

        self.tab_label = tk.Label(
            self.tab_frame,
            text="untitled.py",
            bg="#161625",
            fg="#00e5ff", # neon cyan
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=6
        )
        self.tab_label.pack(side=tk.LEFT)

        # Text Editor
        self.text_area = scrolledtext.ScrolledText(
            right_frame, 
            font=("Consolas", 11), 
            bg="#08080c", # Solid dark background
            fg="#70ffd0", # Bright minty green code text
            insertbackground="white",
            bd=0,
            highlightthickness=1,
            highlightbackground="#161625"
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)

        # Bottom control buttons
        editor_footer = tk.Frame(right_frame, bg="#0d0d14")
        editor_footer.pack(fill=tk.X, pady=(0, 12), padx=12)

        self.btn_copy = tk.Button(
            editor_footer, 
            text="📋 Copy Code", 
            command=self.copy_code, 
            bg="#202030", 
            fg="white", 
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2"
        )
        self.btn_copy.pack(side=tk.LEFT, padx=5, ipady=6)

        self.btn_run = tk.Button(
            editor_footer, 
            text="🌐 Run in Browser", 
            command=self.run_code, 
            bg="#00e676", # Acid Green
            fg="#050505", 
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#00c853"
        )
        self.btn_run.pack(side=tk.LEFT, padx=5, ipady=6)

    def create_status_bar(self):
        self.status_var = tk.StringVar(value="Status: Ready to assist.")
        status_bar = tk.Label(
            self.root, 
            textvariable=self.status_var, 
            bd=0, 
            relief=tk.SUNKEN, 
            anchor=tk.W, 
            bg="#161625", 
            fg="#a5a5cc", 
            font=("Segoe UI", 9),
            padx=10,
            pady=4
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # =========================
    # Process Actions
    # =========================
    def is_casual_talk(self, prompt):
        """साधारण बोलचाल वा हेल्लो-हाई फिल्टर गर्ने"""
        greetings = ["hi", "hello", "hey", "hola", "namaste", "sanchai", "k xa", "k x", "how are you", "who are you", "good morning", "good afternoon"]
        cleaned = prompt.lower().strip().strip("?").strip("!")
        words = cleaned.split()
        
        # यदि १ वा २ वटा शब्द मात्र छ र त्यो greetings सँग मिल्छ भने
        if len(words) <= 3 and any(greet in cleaned for greet in greetings):
            return True
        return False

    def new_chat(self):
        global chat_history, current_code_state
        chat_history = []
        current_code_state = ""
        self.last_filename = ""
        
        if self.typing_job:
            self.root.after_cancel(self.typing_job)
            
        self.text_area.delete("1.0", tk.END)
        self.prompt_entry.delete(0, tk.END)
        
        self.file_list = []
        self.file_listbox.delete(0, tk.END)
        
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.insert(tk.END, "✨ New Session Started.\n🤖 AI: नयाँ प्रोजेक्ट माग गर्नुहोस् वा कुराकानी सुरु गर्नुहोस्।\n\n")
        self.chat_display.config(state=tk.DISABLED)
        
        self.tab_label.config(text="untitled.py")
        self.status_var.set("नयाँ सेसन सुरु भयो।")

    def typewriter_effect(self, code_text):
        """लाइभ टाइपिङ प्रभाव (Typewriter style line-by-line coding)"""
        self.text_area.delete("1.0", tk.END)
        lines = code_text.splitlines()
        
        def insert_line(idx):
            if idx < len(lines):
                self.text_area.insert(tk.END, lines[idx] + "\n")
                self.text_area.see(tk.END)
                # प्रत्येक लाइन देखाउन सानो समय अन्तराल (१२ मिलिसेकेन्ड)
                self.typing_job = self.root.after(12, insert_line, idx + 1)
            else:
                self.typing_job = None
                self.status_var.set(f"✅ Code loading complete.")

        insert_line(0)

    def generate_code(self):
        prompt = self.prompt_entry.get().strip()
        provider = self.provider_var.get()

        if not prompt:
            messagebox.showwarning("Warning", "कृपया केही लेख्नुहोस्!")
            return

        # १. साधारण हेल्लो/हाई चेक गर्ने
        if self.is_casual_talk(prompt):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"👤 User: {prompt}\n")
            self.chat_display.insert(
                tk.END, 
                "🤖 AI: नमस्ते! म कोडिङ गर्ने AI हुँ। मलाई साधारण कुराकानीमा कोड सिर्जना गर्न अनुमति छैन। "
                "कृपया मलाई सिधै कुनै सफ्टवेयर, स्क्रिप्ट, वा वेब पेज सिर्जना गर्न भन्नुहोस् (जस्तै: 'create a registration page' वा 'python simple calculator') "
                "र म तपाईँको लागि कोड तयार पार्नेछु।\n\n"
            )
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.prompt_entry.delete(0, tk.END)
            return

        # २. कोड सिर्जना गर्ने मुख्य कार्य
        existing_code = self.text_area.get("1.0", tk.END).strip()

        # "Thinking..." अवस्था देखाउने
        self.status_var.set("🤖 AI thinking and researching...")
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"👤 User: {prompt}\n")
        self.chat_display.insert(tk.END, f"🤖 AI: Processing request using {provider}... Thinking... 💭\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.root.update_idletasks()

        try:
            # AI इन्जिन कल
            response_text, engine_used = generate_code_from_ai(prompt, provider, existing_code)
            
            # रेस्पोन्स पार्स गर्ने
            explanation = "No explanation provided."
            code_content = ""

            if "[EXPLANATION]" in response_text and "[CODE]" in response_text:
                parts = response_text.split("[CODE]")
                explanation = parts[0].replace("[EXPLANATION]", "").strip()
                code_content = parts[1].strip()
            else:
                # यदि ढाँचा मिलेन भने आफैं छुट्याउने प्रयास गर्ने
                if "[CODE]" in response_text:
                    parts = response_text.split("[CODE]")
                    code_content = parts[1].strip()
                    explanation = parts[0].replace("[EXPLANATION]", "").strip()
                else:
                    code_content = response_text
                    explanation = "Successfully completed the instruction."

            # कोडबाट अनावश्यक Markdown ब्लक हटाउने
            if code_content.startswith("```"):
                lines = code_content.split("\n")
                if len(lines) > 2:
                    code_content = "\n".join(lines[1:-1])

            # च्याट डिस्प्ले र विवरण अपडेट गर्ने
            self.chat_display.config(state=tk.NORMAL)
            # पुरानो 'Thinking...' सन्देश हटाएर वास्तविक विवरण राख्ने
            self.chat_display.insert(tk.END, f"📢 Description (using {engine_used}):\n{explanation}\n\n")
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)

            # लाइभ टाइपिङ प्रभावको साथमा एडिटरमा कोड देखाउने
            self.typewriter_effect(code_content)

            # फाइल सेभ गर्ने र अद्यावधिक गर्ने
            self.last_filename = self.save_code_to_file(code_content)
            basename = os.path.basename(self.last_filename)
            if basename not in self.file_list:
                self.file_list.append(basename)
                self.file_listbox.insert(tk.END, basename)
            
            self.tab_label.config(text=basename)

            # हिस्टोरी मेमोरी सुरक्षित गर्ने
            chat_history.append({"role": "user", "content": prompt})
            chat_history.append({"role": "assistant", "content": response_text})

            self.prompt_entry.delete(0, tk.END)
            self.status_var.set(f"✅ Success: Code generated inside {basename} ({engine_used})")

        except Exception as e:
            self.status_var.set("❌ Processing failed.")
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"❌ Error: System could not generate code. details: {str(e)}\n\n")
            self.chat_display.config(state=tk.DISABLED)
            messagebox.showerror("Error", f"त्रुटि: {str(e)}")

    def save_code_to_file(self, code_text):
        lower = code_text.lower()
        if "html" in lower[:150]:
            filename = "code/index.html"
        elif "javascript" in lower[:150] or "js" in lower[:150]:
            filename = "code/app.js"
        elif "css" in lower[:150]:
            filename = "code/style.css"
        else:
            filename = "code/program.py"

        os.makedirs("code", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_text)
        return filename

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            filename = self.file_listbox.get(selection[0])
            filepath = os.path.join("code", filename)
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if self.typing_job:
                    self.root.after_cancel(self.typing_job)
                
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert(tk.END, content)
                self.tab_label.config(text=filename)
                self.last_filename = filepath

    def copy_code(self):
        code_text = self.text_area.get("1.0", tk.END).strip()
        if code_text:
            pyperclip.copy(code_text)
            self.btn_copy.config(text="✅ Copied!")
            self.root.after(2000, lambda: self.btn_copy.config(text="📋 Copy Code"))

    def run_code(self):
        if self.last_filename and os.path.exists(self.last_filename):
            filepath = os.path.abspath(self.last_filename)
            webbrowser.open(f"file://{filepath}")
        else:
            messagebox.showwarning("File Not Found", "पहिले रन गर्नका लागि कोड तयार गर्नुहोस्।")

# =========================
# Execution Entry
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    app = CoderApp(root)
    root.mainloop()