import threading
import queue
import time
import speech_recognition as sr
import mtranslate


# ==========================================
# थपिएका नयाँ मोड्युलहरू (Voice & Decision)
# ==========================================
class VoiceRecognizer:
    """
    Update garieko kura (k k badliyo):
      1. BACKGROUND ma continuous sunxa (listen_in_background) -
         AI arko kaam gardai garda pani mic bandai hudaina.
      2. User le bolna sakiyena samma pardaikhincha - beech beech ma
         kaatdaina (phrase_time_limit=None), tara chup baseko dherai
         bhaye matra 'complete' manxa (pause_threshold).
      3. Answer chai user le bolna PURA sakepachi matra dincha -
         beech ma kehi bolda ni queue ma rakhxa, ani sabai jodera
         'thumbstop' bhaye pachi matra process/answer garxa.
    """

    def __init__(self, silence_gap=1.5):
        self.stop_speaking = False   # AI bolirako xa vane True garne
        self.is_ai_speaking = False  # AI ko bolne state track garna

        self._recognizer = sr.Recognizer()
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.energy_threshold = 100

        # user le kati bela samma chup baseko lai "bolna sakiyo" manne
        # (paila 3.0 thiyo -> dherai chai testai raख्यो, chai tune garna milxa)
        self._recognizer.pause_threshold = silence_gap

        self._audio_queue = queue.Queue()
        self._text_queue = queue.Queue()
        self._stop_listener = None
        self._mic = sr.Microphone()

    # ---------------------------------------------------
    # Step 1: Microphone calibrate garne (ek choti matra)
    # ---------------------------------------------------
    def calibrate(self):
        print("\n[Setup]: Calibrating microphone...")
        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[System]: Ready! Listening in background...")

    # ---------------------------------------------------
    # Step 2: BACKGROUND ma sadai sunirakhne (non-blocking)
    # ---------------------------------------------------
    def _audio_callback(self, recognizer, audio):
        """Yo function background thread bata auto call huncha
        jaba pani ekchoti user ko complete bolai (phrase) sakincha."""
        self._audio_queue.put(audio)

    def start_background_listening(self):
        self.calibrate()

        # phrase_time_limit=None => user le jati lamo bolyo pani
        # beech ma kaat-dena, sabai pura sunxa.
        self._stop_listener = self._recognizer.listen_in_background(
            self._mic,
            self._audio_callback,
            phrase_time_limit=None,
        )

        # audio -> text convert garne worker thread (background)
        worker = threading.Thread(target=self._recognize_worker, daemon=True)
        worker.start()

    def stop_background_listening(self):
        if self._stop_listener:
            self._stop_listener(wait_for_stop=False)

    # ---------------------------------------------------
    # Step 3: Audio lai text ma convert garne (background)
    # ---------------------------------------------------
    def _recognize_worker(self):
        while True:
            audio = self._audio_queue.get()
            try:
                content = self._recognizer.recognize_google(audio, language='en-ne')

                if content.strip():
                    # 🔥 User bolisakyo -> AI bolirako xa vane rokidiu
                    self.stop_speaking = True
                    self.is_ai_speaking = False

                    print("\r" + " " * 60 + "\r", end="")
                    print(f"You: {content}")

                    self._text_queue.put(content)

            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"\n[Error - API]: {e}")
                continue
            except Exception as e:
                print(f"\n[Error]: {e}")
                continue

    # ---------------------------------------------------
    # Step 4: Main program le yo call garera "final answer"
    # nikalne - user le PURA bolisakepachi matra return huncha
    # ---------------------------------------------------
    def get_command(self, block=True, timeout=None):
        """
        block=True bhaye samma yo function le user ko pura vaneko
        kura nasunun jaba samma wait garxa (queue bata nikalxa).
        Yesle nishchit garxa ki AI le user ko kura ADHA ma answer
        nagari, PURA sunepachi matra process garne.
        """
        try:
            content = self._text_queue.get(block=block, timeout=timeout)
            return content
        except queue.Empty:
            return None

    # ---------------------------------------------------
    # Backward-compatible naam - purano code ma "vr.command()"
    # call gareko thiyo, tyo halka nabhagos vanera yo raakheko.
    # Yesle background listening auto-start garxa (yedi
    # nagareko bhaye) ani user le PURA bolisakepachi text
    # return garxa - purano behaviour jastai nai.
    # ---------------------------------------------------
    def command(self):
        if self._stop_listener is None:
            self.start_background_listening()

        print("\n[System]: Listening... (bolna suru garnus)")
        return self.get_command(block=True)


# ==========================================
# Example usage
# ==========================================
if __name__ == "__main__":
    vr = VoiceRecognizer(silence_gap=1.5)
    vr.start_background_listening()

    print("[System]: Bolna suru garnus... (Ctrl+C le rokna sakinxa)")

    try:
        while True:
            # yesle block garera basxa jaba samma user le PURA
            # ekchoti bolisakdaina (background ma sunidai nai rahanxa)
            command = vr.get_command(block=True)

            if command:
                # ============================
                # Yaha AI ko jawaph/answer logic rakhnus
                # (translate garna chahe yesari garnus)
                # ============================
                # translated = mtranslate.translate(command, "ne-NP", "auto")
                print(f"[AI answering to]: {command}")

    except KeyboardInterrupt:
        vr.stop_background_listening()
        print("\n[System]: Band vayo. Bye!")