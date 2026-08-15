import speech_recognition as sr
import mtranslate




# ==========================================
# थपिएका नयाँ मोड्युलहरू (Voice & Decision)
# ==========================================
class VoiceRecognizer:

    def __init__(self):
        self.stop_speaking = False

    def command(self):
        global stop_speaking

        r = sr.Recognizer()
        r.dynamic_energy_threshold = True 
        r.pause_threshold = 3.0  
        r.energy_threshold = 100

        print("\n[Setup]: Calibrating microphone...")
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=1)
        
        print("[System]: Ready! Listening...")

        while True:
            with sr.Microphone() as source:
                try:
                    print("\rListening... ", end="", flush=True)

                    audio = r.listen(source, timeout=None, phrase_time_limit=5)

                    print("\rRecognizing... ", end="", flush=True)

                    content = r.recognize_google(audio, language='en-ne')

                    if content.strip():
                        # 🔥 AI bolirako xa vane STOP gara
                        stop_speaking = True  

                        #translated_text = mtranslate.translate(content, "ne-NP", "auto")

                        print("\r" + " " * 50 + "\r", end="")
                        print(f"You (EN): {content}")
                        #print(f"Bot (NP): {translated_text}")

                        #return translated_text
                        return content

                except sr.UnknownValueError:
                    continue
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    print(f"\n[Error]: {e}")
                    continue