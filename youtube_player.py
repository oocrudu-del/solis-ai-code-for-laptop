import pywhatkit as pw
import time
import pyautogui
import random

# 🎵 Nepali songs list
NEPALI_SONGS = [
    "nepali song",
    "latest nepali song",
    "nepali love song",
    "nepali sad song",
    "sushant kc song",
    "nepali pop song"
]

# 💔 Sad songs (ghau lagyo case)
SAD_SONGS = [
    "nepali sad song",
    "very emotional nepali song",
    "nepali breakup song",
    "sad nepali song 2024",
    "heart touching nepali song"
]

#========play music on youtube=======
def play_music_on_youtube(song_name):
    if song_name:
        print(f"DIPU: Playing on YouTube -> {song_name}")
        pw.playonyt(song_name)
        time.sleep(5)
        pyautogui.hotkey("k") 
    else:
        print("DIPU: Kun gana bajaune ho maile thaha paina.")


#========random song========
def play_random_nepali_song():
    song = random.choice(NEPALI_SONGS)
    play_music_on_youtube(song)

def play_sad_song():
    song = random.choice(SAD_SONGS)
    play_music_on_youtube(song)

