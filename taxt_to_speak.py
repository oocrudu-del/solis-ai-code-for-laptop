import pygame
import edge_tts
import asyncio
import os
import re
from config import VOICE_PROFILE

# १. Pygame mixer लाई सुरुमै एक पटक मात्र initialize गर्ने (यसले performance राम्रो बनाउँछ)
pygame.mixer.init()

# डिफल्ट आवाजको लिङ्ग सेट गर्ने
CURRENT_GENDER = VOICE_PROFILE  # Use the voice profile from config

#========real laugh function=======
def real_laugh():
    # पटक-पटक mixer.init() गरिरहनु पर्दैन
    try:
        pygame.mixer.music.load("laugh.mp3")
        pygame.mixer.music.play()
    except Exception as e:
        print(f"हास्य फाइल बजाउन समस्या भयो: {e}")

#========speak function=======
async def speak(audio, gender=None):
    global CURRENT_GENDER
    
    if gender is None:
        gender = CURRENT_GENDER

    # १. भाषा पहिचान गर्ने (यदि नेपाली देवनागरी अक्षरहरू छन् भने नेपाली, नत्र अंग्रेजी)
    is_nepali = bool(re.search(r'[\u0900-\u097F]', audio))
    
    # २. भाषा र लिङ्ग अनुसार Voice चयन गर्ने
    if is_nepali:
        if gender.lower() == "male":
            voice = "ne-NP-SagarNeural"  # नेपाली पुरुष आवाज
        else:
            voice = "ne-NP-HemkalaNeural"  # नेपाली महिला आवाज
    else:
        if gender.lower() == "male":
            voice = "en-US-GuyNeural"  # अंग्रेजी पुरुष आवाज
        else:
            voice = "en-US-JennyNeural"  # अंग्रेजी महिला आवाज

    print("SOLIS:", audio)

    # ३. edge_tts बाट अडियो फाइल सेभ गर्ने
    communicate = edge_tts.Communicate(text=audio, voice=voice)
    temp_file = "reply.mp3"
    
    await communicate.save(temp_file)
    
    # ४. Pygame प्रयोग गरेर Non-blocking तरिकाले अडियो बजाउने
    try:
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # अडियो नसकिउन्जेल async रूपमा पर्खिने (यसले प्रोग्राम फ्रिज हुन दिँदैन)
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.05)  # सानो interval मा चेक गर्ने
            
        # ५. फाइल डिलिट गर्नुअघि mixer बाट फाइल अनलोड गर्ने (यसले file lock error रोक्छ)
        pygame.mixer.music.unload()
        
    except Exception as e:
        print(f"अडियो बजाउन समस्या भयो: {e}")
        
    finally:
        # सुरक्षित तरिकाले अस्थायी फाइल डिलिट गर्ने
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except PermissionError:
                # यदि अझै पनि सिस्टमले फाइल लक राखेको छ भने अर्को पटक ओभरराइट हुन दिने
                pass
  
#========command clean=======
def clean_command(audio):
    """Remove special characters and emojis"""
    clean_text = re.sub(r'[^\w\s]', '', audio)  # letters, numbers, space only
    clean_text = re.sub(r'\s+', ' ', clean_text)
    return clean_text.strip().lower()

def process(content):
    pass