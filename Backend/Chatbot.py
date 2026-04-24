from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
from .LanguageManager import language_manager

env_vars      = dotenv_values(".env")
Username      = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey    = env_vars.get("GroqAPIKey")

client   = Groq(api_key=GroqAPIKey)
messages = []

# Base system prompt — NO hardcoded language restriction here.
# Language instruction is injected dynamically via language_manager
# so it switches between Bangla and English automatically.
SystemBase = f"""Hello, I am {Username}. You are my personal AI assistant named {Assistantname}.
You have real-time up-to-date information from the internet and can perform tasks.
*** Do not tell time until I ask. Do not talk too much. Just answer the question. ***
*** Do not provide notes in the output. Never mention your training data. ***
"""

try:
    with open(r"Data\Chatlog.json", "r") as f:
        messages = load(f)
except FileNotFoundError:
    with open(r"Data\Chatlog.json", "w") as f:
        dump([], f)

def RealtimeInformation():
    now  = datetime.datetime.now()
    data = "Please use this real-time information if needed:\n"
    data += f"Day: {now.strftime('%A')}\n"
    data += f"Date: {now.strftime('%d')}\n"
    data += f"Month: {now.strftime('%B')}\n"
    data += f"Year: {now.strftime('%Y')}\n"
    data += f"Time: {now.strftime('%H')} hours, {now.strftime('%M')} minutes, {now.strftime('%S')} seconds.\n"
    return data

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    return '\n'.join(line for line in lines if line.strip())

def _build_system_chatbot():
    """
    Build system messages with the CURRENT language reply instruction.
    Called fresh every time ChatBot() is called so language switches
    take effect immediately — no restart needed.
    """
    lang_instruction = language_manager.get_reply_instruction()
    full_system      = SystemBase + "\n" + lang_instruction

    # DEBUG — uncomment to verify the instruction is correct
    # print(f"[Chatbot] System instruction tail: ...{full_system[-120:]}")

    return [{"role": "system", "content": full_system}]

def ChatBot(Query):
    """
    Send the user's query to the AI.
    Automatically replies in Bangla or English based on detected language.
    """
    try:
        with open(r"Data\Chatlog.json", "r") as f:
            messages = load(f)

        messages.append({"role": "user", "content": f"{Query}"})

        SystemChatBot = _build_system_chatbot()

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=(
                SystemChatBot
                + [{"role": "system", "content": RealtimeInformation()}]
                + messages
            ),
            max_tokens=1024,
            temperature=0.7,
            top_p=1,
            stream=True,
            stop=None
        )

        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content

        Answer = Answer.replace("</s>", "")
        messages.append({"role": "assistant", "content": Answer})

        with open(r"Data\Chatlog.json", "w") as f:
            dump(messages, f, indent=4)

        return AnswerModifier(Answer)

    except Exception as e:
        print(f"Error in ChatBot: {e}")
        with open(r"Data\Chatlog.json", "w") as f:
            dump([], f, indent=4)
        return ChatBot(Query)

if __name__ == "__main__":
    while True:
        print(ChatBot(input("Enter Your Question: ")))