import random
import asyncio
import edge_tts
import os
from Backend.Config import get_env
from .LanguageManager import language_manager

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

_DefaultVoice = get_env("AssistantVoice", "en-CA-LiamNeural")

def _get_voice() -> str:
    """Get the correct TTS voice for the currently detected language."""
    try:
        return language_manager.get_tts_voice()
    except Exception:
        return _DefaultVoice

async def TextToAudioFile(text: str) -> None:
    """Convert text to an MP3 audio file using the correct voice."""
    file_path = r"Data\speech.mp3"

    if os.path.exists(file_path):
        os.remove(file_path)

    voice = _get_voice()

    # Different pitch/rate per language for natural sound
    if language_manager.is_bangla():
        pitch = "+0Hz"
        rate  = "+8%"
    else:
        pitch = "+5Hz"
        rate  = "+13%"

    communicate = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
    await communicate.save(r'Data\speech.mp3')

def TTS(Text, func=lambda r=None: True):
    """Play text as speech using the currently active language's voice."""
    try:
        asyncio.run(TextToAudioFile(Text))

        pygame.mixer.init()
        pygame.mixer.music.load(r"Data\speech.mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if func() == False:
                break
            pygame.time.Clock().tick(10)

        return True

    except Exception as e:
        print(f"Error in TTS: {e}")
        return False

    finally:
        try:
            func(False)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception as e:
            print(f"Error in TTS cleanup: {e}")

def TextToSpeech(Text, func=lambda r=None: True):
    """
    Speak the given text. If text is very long, reads a summary
    and directs the user to the chat screen.
    Automatically uses the correct voice for the active language.
    """
    Data = str(Text).split(".")

    responses_en = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
    ]

    responses_bn = [
        "বাকি উত্তর চ্যাট স্ক্রিনে দেখতে পাবেন।",
        "বাকি অংশ চ্যাট স্ক্রিনে দেখুন।",
        "পুরো উত্তর চ্যাট স্ক্রিনে দেওয়া হয়েছে।",
        "বিস্তারিত চ্যাট স্ক্রিনে দেখুন।",
        "চ্যাট স্ক্রিনে বাকি তথ্য পাবেন।",
    ]

    responses = responses_bn if language_manager.is_bangla() else responses_en

    if len(Data) > 4 and len(Text) >= 250:
        return TTS(
            ".".join(Text.split(".")[0:2]) + "." + random.choice(responses),
            func
        )
    else:
        return TTS(Text, func)

if __name__ == "__main__":
    while True:
        TextToSpeech(input("Enter the text: "))
