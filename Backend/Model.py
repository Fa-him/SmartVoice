import cohere
from rich import print
from Backend.Config import require_env

co = cohere.Client(api_key=require_env("CohereAPIKey"))

# Define a list of recognized function keywords for task categorization.
funcs = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "youtube control", "reminder", "language" 
]

# Initialize an empty list to store user messages.
messages = []

def _is_task_start(task: str) -> bool:
    return any(task.startswith(func) for func in funcs)

def ParseDecisionResponse(response_text: str):
    response_parts = response_text.replace("\n", "").split(",")
    tasks = []

    for part in response_parts:
        part = part.strip()
        if not part:
            continue

        if _is_task_start(part):
            tasks.append(part)
        elif tasks:
            tasks[-1] = f"{tasks[-1]}, {part}"

    return [task for task in tasks if _is_task_start(task)]

# Define the preamble that guides the AI model on how to categorize queries.
preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information like if the query is 'who was akbar?' respond with 'general who was akbar?', if the query is 'how can i study more effectively?' respond with 'general how can i study more effectively?', if the query is 'can you help me with this math problem?' respond with 'general can you help me with this math problem?', if the query is 'Thanks, i really liked it.' respond with 'general thanks, i really liked it.' , if the query is 'what is python programming language?' respond with 'general what is python programming language?', etc. Respond with 'general (query)' if a query doesn't have a proper noun or is incomplete like if the query is 'who is he?' respond with 'general who is he?', if the query is 'what's his networth?' respond with 'general what's his networth?', if the query is 'tell me more about him.' respond with 'general tell me more about him.', and so on even if it require up-to-date information to answer. Respond with 'general (query)' if the query is asking about time, day, date, month, year, etc like if the query is 'what's the time?' respond with 'general what's the time?'.
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date information like if the query is 'who is indian prime minister' respond with 'realtime who is indian prime minister', if the query is 'tell me about facebook's recent update.' respond with 'realtime tell me about facebook's recent update.', if the query is 'tell me news about coronavirus.' respond with 'realtime tell me news about coronavirus.', etc and if the query is asking about any individual or thing like if the query is 'who is akshay kumar' respond with 'realtime who is akshay kumar', if the query is 'what is today's news?' respond with 'realtime what is today's news?', if the query is 'what is today's headline?' respond with 'realtime what is today's headline?', etc.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram', etc. but if the query is asking to open multiple applications, respond with 'open 1st application name, open 2nd application name' and so on.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc. but if the query is asking to close multiple applications or websites, respond with 'close 1st application name, close 2nd application name' and so on.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go', etc. but if the query is asking to play multiple songs, respond with 'play 1st song name, play 2nd song name' and so on.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt like 'generate image of a lion', 'generate image of a cat', etc. but if the query is asking to generate multiple images, respond with 'generate image 1st image prompt, generate image 2nd image prompt' and so on.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder like 'set a reminder at 9:00pm on 25th june for my business meeting.' respond with 'reminder 9:00pm 25th june business meeting'.
-> Respond with 'reminder (recurring reminder request)' if a query is requesting a recurring reminder like 'remind me every day at 8 pm to study' respond with 'reminder every day at 8 pm to study'.
-> Respond with 'reminder list' if the user asks to show, list, view, or check their reminders.
-> Respond with 'reminder cancel (details)' if the user asks to cancel, delete, remove, or clear reminders. Example: 'cancel my medicine reminder' respond with 'reminder cancel medicine'.
-> Respond with 'reminder snooze (duration)' if the user asks to snooze, delay, or postpone a recent reminder. Example: 'snooze this for 10 minutes' respond with 'reminder snooze 10 minutes'.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc. but if the query is asking to do multiple tasks, respond with 'system 1st task, system 2nd task', etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content like application, codes, emails or anything else about a specific topic but if the query is asking to write multiple types of content, respond with 'content 1st topic, content 2nd topic' and so on.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google but if the query is asking to search multiple topics on google, respond with 'google search 1st topic, google search 2nd topic' and so on.
-> Respond with 'youtube control resume' if the user says only 'play', 'resume', or 'unpause' to control the current YouTube video. Do not use 'play' unless the user gives a song or video name.
-> Respond with 'youtube control (action)' if the user wants to control an already-playing YouTube video. For example: 'pause the video' respond with 'youtube control pause', 'resume the video' respond with 'youtube control resume', 'make it fullscreen' respond with 'youtube control fullscreen', 'turn on captions' respond with 'youtube control captions', 'theater mode' respond with 'youtube control theater', 'ambient mode' respond with 'youtube control ambient', 'turn on autoplay' respond with 'youtube control autoplay', 'set speed to 1.5' respond with 'youtube control speed 1.5', 'slow down the video' respond with 'youtube control slow down', 'set a sleep timer for 30 minutes' respond with 'youtube control sleep timer 30', 'cancel the timer' respond with 'youtube control cancel timer', 'skip forward 10 seconds' respond with 'youtube control skip forward 10', 'skip back 10 seconds' respond with 'youtube control skip backward 10', 'volume 70' respond with 'youtube control volume 70', 'mute the video' respond with 'youtube control mute', 'next video' respond with 'youtube control next video', 'what is playing' respond with 'youtube control status', 'close youtube' respond with 'youtube control close youtube'.
-> Respond with 'language english' if the user wants to switch to English mode. Example: 'switch to english', 'speak english', 'english mode' → 'language english'.
-> Respond with 'language bangla' if the user wants to switch to Bangla mode. Example: 'বাংলায় বলো', 'switch to bangla', 'bangla mode' → 'language bangla'.
*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye mamur_beta.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""

# Define a chat history with predefined user-chatbot interactions for context.
ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "do you like pizza?"},
    {"role": "Chatbot", "message": "general do you like pizza?"},
    {"role": "User", "message": "open chrome and tell me about Elon Musk"},
    {"role": "Chatbot", "message": "open chrome, general tell me about Elon Musk"},
    {"role": "User", "message": "open chrome and edge"},
    {"role": "Chatbot", "message": "open chrome, open edge"},
    {"role": "User", "message": "what is today's date and by the way remind me that i have a job interview on 20th sep at 10 am"},
    {"role": "Chatbot", "message": "general what is today's date, reminder 10:00am 20th sep job interview"},
    {"role": "User", "message": "chat with me."},
    {"role": "Chatbot", "message": "general chat with me."}
]

# Define the main function for decision-making on queries.
def FirstlayerDMM(prompt: str = "test"):
    # Add the user's query to the messages list.
    messages.append({"role": "user", "content": f"{prompt}"})

    # Use direct chat (non-streaming) - MUCH FASTER
    response_obj = co.chat(
        model='command-r-08-2024',  # or whatever model you chose
        message=prompt,
        temperature=0.7,
        chat_history=ChatHistory,
        prompt_truncation='OFF',
        preamble=preamble
    )

    response = response_obj.text

    response = ParseDecisionResponse(response)

    if not response or any("(query)" in task for task in response):
        return [f"general {prompt}"]

    return response  # Return the filtered response.

# Entry point for the script.
if __name__ == "__main__":
    # Continuously prompt the user for input and process it.
    while True:
        print(FirstlayerDMM(input(">>> ")))  # Print the categorized response.
