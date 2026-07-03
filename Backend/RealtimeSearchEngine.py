import requests
from groq import Groq
from json import JSONDecodeError, load, dump
import datetime
from Backend.Config import get_env, require_env
from .LanguageManager import language_manager

Username      = get_env("Username", "User")
Assistantname = get_env("Assistantname", "SmartVoice")
SerperAPIkey  = get_env("SerperAPIkey")
client        = Groq(api_key=require_env("GroqAPIKey"))

# Base system prompt — language instruction injected dynamically below
SystemBase = f"""Hello, I am {Username}. You are a very accurate and advanced AI assistant named {Assistantname} with real-time up-to-date information from the internet.
*** Provide answers in a professional way. Use proper grammar, punctuation, and sentence structure. ***
*** Answer only from the provided data. Do not talk too much. ***
*** Do not provide notes. Never mention your training data. ***
"""

def _load_messages():
    try:
        with open(r"Data\Chatlog.json", "r") as f:
            return load(f)
    except (FileNotFoundError, JSONDecodeError):
        with open(r"Data\Chatlog.json", "w") as f:
            dump([], f)
        return []


def _save_messages(chat_messages):
    with open(r"Data\Chatlog.json", "w") as f:
        dump(chat_messages, f, indent=4)


messages = _load_messages()

def SerperSearch(query):
    if not SerperAPIkey:
        return f"Could not search for '{query}' — API key missing."

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            json={"q": query},
            headers={'X-API-KEY': SerperAPIkey, 'Content-Type': 'application/json'},
            timeout=5
        )
        response.raise_for_status()
        results = response.json().get('organic', [])[:5]

        if not results:
            return f"No search results found for '{query}'."

        Answer = f"The search results for '{query}' are:\n[start]\n"
        for r in results:
            Answer += f"Title: {r.get('title','')}\nDescription: {r.get('snippet','')}\n\n"
        Answer += "[end]"
        return Answer

    except Exception as e:
        return f"Search error: {e}"

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    return '\n'.join(line for line in lines if line.strip())

def Information():
    now  = datetime.datetime.now()
    data = "Real-time information:\n"
    data += f"Day: {now.strftime('%A')}, Date: {now.strftime('%d')} "
    data += f"{now.strftime('%B')} {now.strftime('%Y')}, "
    data += f"Time: {now.strftime('%H')}:{now.strftime('%M')}:{now.strftime('%S')}\n"
    return data

def _build_system_chatbot():
    """
    Build system messages with the CURRENT language reply instruction.
    Called fresh on every RealtimeSearchEngine() call.
    """
    lang_instruction = language_manager.get_reply_instruction()
    full_system      = SystemBase + "\n" + lang_instruction
    return [
        {"role": "system",    "content": full_system},
        {"role": "user",      "content": "Hi"},
        {"role": "assistant", "content": "Hello, how can I help you?"}
    ]

def RealtimeSearchEngine(prompt):
    """
    Search the web and reply in the currently active language (Bangla or English).
    """
    global messages

    try:
        messages = _load_messages()
        messages.append({"role": "user", "content": f"{prompt}"})

        SystemChatBot = _build_system_chatbot()
        SystemChatBot.append({"role": "system", "content": SerperSearch(prompt)})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=(
                SystemChatBot
                + [{"role": "system", "content": Information()}]
                + messages
            ),
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=True,
            stop=None
        )

        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content

        Answer = Answer.strip().replace("</s>", "")
        messages.append({"role": "assistant", "content": Answer})

        _save_messages(messages)

        return AnswerModifier(Answer)

    except Exception as e:
        print(f"Error in RealtimeSearchEngine: {e}")
        return (
            "Sorry, I could not complete the realtime search right now. "
            "Please check the Groq/Serper API keys and network connection."
        )

if __name__ == "__main__":
    while True:
        print(RealtimeSearchEngine(input("Query: ")))
