# Import required libraries
from AppOpener import close, open as appopen
from webbrowser import open as webopen
from pywhatkit import search, playonyt
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from rich import print
from groq import Groq
import webbrowser
import subprocess
import requests
import keyboard
import asyncio
import os
from ddgs import DDGS

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey") # Retrieve the Groq API key.

# Define CSS classes for parsing specific elements in HTML content.
classes = ["zCubwf", "hgKElc", "LTKOO sY7ric", "Z0LcW", "gsrt vk_bk FzvWSb YwPhnf", "pclqee", 
           "tw-Data-text tw-text-small tw-ta",
           "IZ6rdc", "O5uR6d LTKOO", "vLzY6d", "webanswers-webanswers_table__webanswers-table", 
           "dDoNo ikb48b gsrt", "sXLAoe",
           "LWkfKe", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"]

# Define a user-agent for making web requests.
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

# Initialize the Groq client with the API key.
client = Groq(api_key=GroqAPIKey)

# Predefined professional responses for user interactions.
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need-don't hesitate to ask.",
]

# List to store chatbot messages.
messages = []

# System message to provide context to the chatbot.
SystemChatBot = [{"role": "system", "content": f"Hello, I am {os.environ['Username']}, You're a content writer. You have to write content like lette"}]

# Function to perform a Google search.
def GoogleSearch(Topic):
    search(Topic) # Use pywhatkit's search function to perform a Google search.
    return True # Indicate success.

# Function to generate content using AI and save it to a file.
def Content(Topic):

    # Nested function to open a file in Notepad.
    def OpenNotepad(File):
        default_text_editor = 'notepad.exe' # Default text editor.
        subprocess.Popen([default_text_editor, File]) # Open the file in Notepad.
    
    # Nested function to generate content using the AI chatbot.
    def ContentWriterAI(prompt):
        messages.append({"role": "user", "content": f"{prompt}"}) # Add the user's prompt to messages.
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Specify the AI model.
            messages=SystemChatBot + messages, # Include system instructions and chat history.
            max_tokens=2048, # Limit the maximum tokens in the response.
            temperature=0.7, # Adjust response randomness.
            top_p=1, # Use nucleus sampling for response diversity.
            stream=True, # Enable streaming response.
            stop=None, # Allow the model to determine stopping conditions.
        )
        
        Answer = "" # Initialize an empty string for the response.
        
        # Process streamed response chunks.
        for chunk in completion:
            if chunk.choices[0].delta.content: # Check for content in the current chunk.
                Answer += chunk.choices[0].delta.content # Append the content to the answer.
        
        Answer = Answer.replace("</s>", "") # Remove unwanted tokens from the response.
        messages.append({"role": "assistant", "content": Answer}) # Add the AI's response to messages.
        return Answer
        
    Topic = str(Topic).replace("content ", "") # Remove "content " from the topic.
    ContentByAI = ContentWriterAI(Topic) # Generate content using AI.
    
    # Save the generated content to a text file.
    with open(rf"Data\{Topic.lower().replace(' ', '')}.txt", "w", encoding="utf-8") as file:
        file.write(ContentByAI) # Write the content to the file.
        file.close()
        
    OpenNotepad(rf"Data\{Topic.lower().replace(' ', '')}.txt") # Open the file in Notepad.
    return True # Indicate success.


# Function to search for a topic on YouTube.
def YouTubeSearch(Topic):
    Url4Search = f"https://www.youtube.com/results?search_query={Topic}" # Construct the YouTube search URL.
    webbrowser.open(Url4Search) # Open the search URL in a web browser.
    return True # Indicate success.

# Function to play a video on YouTube.
def PlayYoutube(query):
    playonyt(query) # Use pywhatkit's playonyt function to play the video.
    return True # Indicate success.

# Function to handle YouTube player control commands.
# Runs synchronously inside asyncio.to_thread so it doesn't block the event loop.
def YouTubeControl(command):
    try:
        from Backend.YouTubeController import yt_controller
        result = yt_controller.parse_and_execute(command)
        return result
    except ImportError:
        print("[Automation] YouTubeController not found in Backend folder.")
        return "YouTube controller module is missing."
    except Exception as e:
        print(f"[Automation] YouTubeControl error: {e}")
        return f"YouTube control failed: {str(e)[:80]}"

# Function to open an application or a relevant webpage.
def OpenApp(app):

    official_sites = {
    # Search & Browsers
    "google": "https://www.google.com",
    "bing": "https://www.bing.com",
    "yahoo": "https://www.yahoo.com",
    "duckduckgo": "https://duckduckgo.com",

    # Video & Streaming
    "youtube": "https://www.youtube.com",
    "netflix": "https://www.netflix.com",
    "hulu": "https://www.hulu.com",
    "disney+": "https://www.disneyplus.com",
    "amazon prime": "https://www.primevideo.com",
    "twitch": "https://www.twitch.tv",
    "spotify": "https://www.spotify.com",
    "soundcloud": "https://soundcloud.com",

    # Social Media
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",  
    "x": "https://x.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "pinterest": "https://www.pinterest.com",
    "tiktok": "https://www.tiktok.com",
    "snapchat": "https://www.snapchat.com",

    # Communication
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "yahoo mail": "https://mail.yahoo.com",
    "protonmail": "https://protonmail.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "messenger": "https://www.messenger.com",
    "discord": "https://discord.com",
    "slack": "https://slack.com",

    # Shopping & E-commerce
    "amazon": "https://www.amazon.com",
    "ebay": "https://www.ebay.com",
    "walmart": "https://www.walmart.com",
    "aliexpress": "https://www.aliexpress.com",
    "etsy": "https://www.etsy.com",
    "flipkart": "https://www.flipkart.com",
    # Bangladesh
    "daraz": "https://www.daraz.com.bd",
    "ajkerdeal": "https://ajkerdeal.com",
    "othoba": "https://www.othoba.com",
    "chaldal": "https://chaldal.com",
    "evaly": "https://evaly.com.bd",

    # Productivity
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "google slides": "https://slides.google.com",
    "google maps": "https://maps.google.com",
    "microsoft office": "https://www.office.com",
    "onedrive": "https://onedrive.live.com",
    "notion": "https://www.notion.so",
    "trello": "https://trello.com",
    "evernote": "https://evernote.com",
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",

    # News
    "cnn": "https://www.cnn.com",
    "bbc": "https://www.bbc.com",
    "nytimes": "https://www.nytimes.com",
    "guardian": "https://www.theguardian.com",
    "forbes": "https://www.forbes.com",
    "reuters": "https://www.reuters.com",
    # Bangladesh
    "prothom alo": "https://www.prothomalo.com",
    "bd news24": "https://bdnews24.com",
    "the daily star": "https://www.thedailystar.net",
    "jugantor": "https://www.jugantor.com",
    "ittefaq": "https://www.ittefaq.com.bd",
    "kalerkantho": "https://www.kalerkantho.com",

    # Education
    "wikipedia": "https://www.wikipedia.org",
    "khan academy": "https://www.khanacademy.org",
    "coursera": "https://www.coursera.org",
    "udemy": "https://www.udemy.com",
    "edx": "https://www.edx.org",
    "udacity": "https://www.udacity.com",
    "quizlet": "https://quizlet.com",
    # Bangladesh
    "nu": "https://www.nu.ac.bd",
    "du": "https://www.du.ac.bd",
    "buet": "https://www.buet.ac.bd",
    "bauet": "https://www.bauet.ac.bd",
    "cu": "https://www.cu.ac.bd",
    "ru": "https://www.ru.ac.bd",
    "bracu": "https://www.bracu.ac.bd",
    "nsu": "https://www.northsouth.edu",
    "aiub": "https://www.aiub.edu"

    # Government & Services (Bangladesh)
    ,"pmo": "https://pmo.gov.bd",
    "bangladesh.gov": "https://bangladesh.gov.bd",
    "brta": "https://brta.gov.bd",
    "biman": "https://www.biman-airlines.com",
    "bkash": "https://www.bkash.com",
    "nagad": "https://nagad.com.bd",
    "rocket": "https://www.dutchbanglabank.com/rocket/"
}

    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        print(f"Successfully opened the '{app}' application.")
        return True

    except Exception:
        app_lower = app.lower()
        if app_lower in official_sites:
            print(f"Opening official site for '{app}'.")
            webopen(official_sites[app_lower])
            return True
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(app, max_results=5))

            if results:
                for r in results:
                    link = r.get("href", "")
                    if "wikipedia.org" not in link:
                        webopen(link)
                        return True
                print(f"Only Wikipedia results found for '{app}'.")
                return False
            else:
                print(f"Could not find any online results for '{app}'.")
                return False

        except Exception as search_error:
            print(f"An error occurred during the web search: {search_error}")
            return False

# Function to close an application.
def CloseApp(app):

    if "chrome" in app:
        pass # Skip if the app is Chrome.
    else:
        try:
            close(app, match_closest=True, output=True, throw_error=True) # Attempt to close the app.
            return True # Indicate success.
        except:
            return False # Indicate failure.

# Function to execute system-level commands.
def System(command):

    # Nested function to mute the system volume.
    def mute():
        keyboard.press_and_release("volume mute") # Simulate the mute key press.
    
    # Nested function to unmute the system volume.
    def unmute():
        keyboard.press_and_release("volume mute") # Simulate the unmute key press.
    
    # Nested function to increase the system volume.
    def volume_up():
        keyboard.press_and_release("volume up") # Simulate the volume up key press.
    
    # Nested function to decrease the system volume.
    def volume_down():
        keyboard.press_and_release("volume down") # Simulate the volume down key press.
    
    # Execute the appropriate command.
    if command == "mute":
        mute()
    elif command == "unmute":
        unmute()
    elif command == "volume up":
        volume_up()
    elif command == "volume down":
        volume_down()
    
    return True # Indicate success.

# Asynchronous function to translate and execute user commands.
async def TranslateAndExecute(commands: list[str]):

    funcs = [] # List to store asynchronous tasks.
    
    for command in commands:

        if command.startswith("open "): # Handle "open" commands.

            if "open it" in command: # Ignore "open it" commands.
                pass

            if "open file" == command: # Ignore "open file" commands.
                pass

            else:
                fun = asyncio.to_thread(OpenApp, command.removeprefix("open ")) # Schedule app opening.
                funcs.append(fun)
        
        elif command.startswith("general "): # Placeholder for general commands.
            pass

        elif command.startswith("realtime "): # Placeholder for real-time commands.
            pass
            
        elif command.startswith("close "): # Handle "close" commands.
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close ")) # Schedule app closing.
            funcs.append(fun)

        elif command.startswith("play "): # Handle "play" commands.
            fun = asyncio.to_thread(PlayYoutube, command.removeprefix("play ")) # Schedule YouTube playback.
            funcs.append(fun)
            
        elif command.startswith("content "): # Handle "content" commands.
            fun = asyncio.to_thread(Content, command.removeprefix("content ")) # Schedule content creation.
            funcs.append(fun)

        elif command.startswith("google search "): # Handle Google search commands.
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search ")) # Schedule Google search.
            funcs.append(fun)
            
        elif command.startswith("youtube search "): # Handle YouTube search commands.
            fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search ")) # Schedule YouTube search.
            funcs.append(fun)
            
        elif command.startswith("system "): # Handle system commands.
            fun = asyncio.to_thread(System, command.removeprefix("system ")) # Schedule system command.
            funcs.append(fun)

        elif command.startswith("youtube control "): # Handle YouTube player control commands.
            fun = asyncio.to_thread(YouTubeControl, command.removeprefix("youtube control ")) # Schedule YouTube control.
            funcs.append(fun)
            
        else:
            print(f"No Function Found. For {command}") # Print an error for unrecognized commands.
            
    results = await asyncio.gather(*funcs) # Execute all tasks concurrently.
    
    for result in results: # Process the results.
        if isinstance(result, str):
            yield result
        else:
            yield result

# Asynchronous function to automate command execution.
async def Automation(commands: list[str]):

    async for result in TranslateAndExecute(commands): # Translate and execute commands.
        pass
        
    return True # Indicate success.

# if __name__ == "__main__":
#     asyncio.run(Automation(["open facebook", "open instagram", "open telegram", "play Gibran Idea 10", "content song for me"]))