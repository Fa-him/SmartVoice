# import pygame
# import time

# pygame.init()
# pygame.mixer.init()

# # 1. Use a raw string (r"") for the path
# # 2. Ensure the filename and extension match exactly
# path = r"Data\Adam Oh - Trapped In My Mind (Lyrics _ Lyric Video(MP3_160K).mp3"

# try:
#     test_sound = pygame.mixer.Sound(path)
#     test_sound.play()
    
#     # Keep the script alive so you can hear it
#     print("Playing sound... Press Ctrl+C to stop.")
#     while pygame.mixer.get_busy():
#         time.sleep(1) 
        
# except pygame.error as e:
#     print(f"Could not load file: {e}")


# import asyncio
# import edge_tts
# import os

# async def clean_test():
#     # 1. Use a standard voice first to rule out voice-specific bugs
#     voice = "en-CA-LiamNeural" 
#     text = "The quick brown fox jumps over the lazy dog."
#     output = "test_output.mp3"

#     print(f"Checking connection for {voice}...")
    
#     # 2. Initialize with basic parameters
#     # Note: pitch and rate can sometimes cause 'No Audio' if formatted incorrectly
#     # Try with NO pitch/rate first.
#     communicate = edge_tts.Communicate(text, voice)
    
#     try:
#         await communicate.save(output)
#         if os.path.exists(output) and os.path.getsize(output) > 0:
#             print("✅ SUCCESS! Audio file 'test_output.mp3' created.")
#             print("You can now add back your custom 'en-CA-LiamNeural' voice.")
#         else:
#             print("❌ File created but is empty. Possible server-side block.")
#     except Exception as e:
#         print(f"❌ Error: {e}")
#         print("\n--- TROUBLESHOOTING TIP ---")
#         print("If you are using a VPN, turn it OFF.")
#         print("If you are in a restricted network (Office/School), the WebSocket may be blocked.")

# if __name__ == "__main__":
#     asyncio.run(clean_test())

import asyncio
import edge_tts
import sys

TEXT = "Hello, world! This is a test of the edge-tts library in Python."
VOICE = "en-US-AvaMultilingualNeural"  # Example voice, use --list-voices to find others
OUTPUT_FILE = "hello.mp3"

async def main():
    try:
        # Create a TTS communicator object
        communicate = edge_tts.Communicate(TEXT, VOICE)
        
        # Write the audio to a file
        with open(OUTPUT_FILE, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
        
        print(f"Audio saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
