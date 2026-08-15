


def classify_intent(text):
    """Decision Making Model"""
    sys_words = ["open", "close","exam", "volume", "shutdown", "minimize", "desktop", "play","send", "search","stop", "restart", "logout", "lock off", "take a screenshot", "scroll", "delete all", "mute","time", "date", "wikipedia", "create file", "delete file", "find file", "create folder", "delete folder", "find folder", "open folder", "close folder", "ghau lagyo", "malai ghau", "play nepali song", "code delete", "file delete", "ai delete", "system delete", "hack "]
    #vis_words = ["see my screen", "k gardaichhu", "what am i doing", "look at this"]
    rel_words = ["who ","news"]
   # my_words = ["my name","your name", "my birthday", "my father", "my mother", "my sister","tell me about myself","about yourself","your features","your capabilities"]
   # emo_words = ["face hera", "kasto dekhinchhu", "analyze my face", "look at me", "mero emotion"]
    img_words = ["generate",  "draw", "image" ]
    
    #if any(w in text for w in vis_words): return "VISION"
    if any(w in text for w in sys_words): return "SYSTEM"
    if any(w in text for w in rel_words): return "RELATIONSHIP"
   # if any(w in text for w in my_words): return "MY_INFO"
    #if any(w in text for w in emo_words): return "EMOTION"
    if any(w in text for w in img_words): return "IMAGE"

    return "LLM"

