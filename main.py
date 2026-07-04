import sys

from Backend.SetupWizard import ensure_user_config

if __name__ == "__main__" and not ensure_user_config():
    sys.exit(0)

from PyQt5.QtWidgets import QApplication
from Frontend.GUI import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus,
    GetTextQuery,
    ClearTextQuery)
from Backend.Model import FirstlayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition, SpeechRecognitionError, TranslateToEnglish
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from Backend.PerformanceLogger import logger
from Backend.SimpleDecisionMaker import SimplePatternMatcher
from Backend.LanguageManager import language_manager
from Backend.Config import get_env, require_env
from Backend.ReminderManager import pop_due_reminders
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import time

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

Username      = get_env("Username", "User")
Assistantname = get_env("Assistantname", "SmartVoice")
DefaultMessage = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. What can I assist you with?'''
subprocesses = []
Functions = ["open", "close", "play", "system", "google search",
             "youtube search", "youtube control", "reminder"]

pattern_matcher = SimplePatternMatcher()
COMPARISON_MODE = True

def IsAutomationCommand(command):
    return any(command == func or command.startswith(func + " ") for func in Functions)

def ContentSpeechText(Answer):
    text = Answer.strip()
    lower_text = text.lower()
    code_markers = [
        "```", "#include", "int main", "using namespace", "public static",
        "def ", "class ", "function ", "console.log", "return ",
    ]

    if text and len(text) <= 900 and not any(marker in lower_text for marker in code_markers):
        return text

    if language_manager.is_bangla():
        return "আমি কনটেন্টটা চ্যাটে লিখে দিয়েছি। আপনি কপি করতে পারবেন।"

    return "I wrote it in the chat. You can copy it from the document card."

def ShowDefaultChatIfNotChats():
    try:
        File    = open(r'Data\ChatLog.json', "r", encoding='utf-8')
        content = File.read()
        File.close()
        stripped_content = content.strip()
        try:
            parsed_content = json.loads(stripped_content) if stripped_content else []
        except json.JSONDecodeError:
            parsed_content = None

        if parsed_content == []:
            with open(r'Data\ChatLog.json', 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write("")
            with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
                file.write("")
            return

        if len(content) < 5:
            with open(r'Data\ChatLog.json', 'w', encoding='utf-8') as f:
                json.dump([
                    {"role": "user",      "content": "Hello."},
                    {"role": "assistant", "content": "Hello, how can I assist you today?"}
                ], f, indent=4)
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write("")
    except FileNotFoundError:
        with open(r'Data\ChatLog.json', 'w', encoding='utf-8') as f:
            json.dump([
                {"role": "user",      "content": "Hello."},
                {"role": "assistant", "content": "Hello, how can I assist you today?"}
            ], f, indent=4)
    except Exception as e:
        print(f"Error in ShowDefaultChatIfNotChats: {e}")
    with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
        file.write(DefaultMessage)

def ReadChatLogJson():
    try:
        with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError:
        print("[WARN] Chatlog.json corrupted. Resetting...")
        default_chatlog = [
            {"role": "user",      "content": "Hello."},
            {"role": "assistant", "content": "Hello, how can I assist you today?"}
        ]
        with open(r'Data\ChatLog.json', 'w', encoding='utf-8') as file:
            json.dump(default_chatlog, file, indent=4)
        return default_chatlog
    except Exception as e:
        print(f"Error in ReadChatLogJson: {e}")
        return []

def ChatLogIntegration():
    try:
        json_data         = ReadChatLogJson()
        formatted_chatlog = ""
        for entry in json_data:
            if entry["role"] == "user":
                formatted_chatlog += f"User: {entry['content']}\n"
            elif entry["role"] == "assistant":
                formatted_chatlog += f"Assistant: {entry['content']}\n"
        formatted_chatlog = formatted_chatlog.replace("User",      Username + " ")
        formatted_chatlog = formatted_chatlog.replace("Assistant", Assistantname + " ")
        with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
            file.write(AnswerModifier(formatted_chatlog))
    except Exception as e:
        print(f"Error in ChatLogIntegration: {e}")

def ShowChatsOnGUI():
    try:
        File = open(TempDirectoryPath('Database.data'), "r", encoding='utf-8')
        Data = File.read()
        if len(str(Data)) > 0:
            result = '\n'.join(Data.split('\n'))
            File.close()
            File = open(TempDirectoryPath('Responses.data'), "w", encoding='utf-8')
            File.write(result)
            File.close()
    except Exception as e:
        print(f"Error in ShowChatsOnGUI: {e}")

def InitialExecution():
    try:
        SetMicrophoneStatus("False")
        ShowTextToScreen("")
        ShowDefaultChatIfNotChats()
        ChatLogIntegration()
        ShowChatsOnGUI()
        print("[OK] Mamur Beta initialized successfully!")
        print(f"[Language] Default language: {language_manager.get_current_language_name()}")
    except Exception as e:
        print(f"[ERROR] Initialization error: {e}")

def MainExecution():

    start_time           = time.time()
    TaskExecution        = False
    ImageExecution       = False
    ImageGenerationQuery = ""

    # ── Duck YouTube volume BEFORE mic opens ──────────────────────────────────
    try:
        from Backend.YouTubeController import yt_controller
        yt_controller.duck_volume(duck_to=8)
    except Exception as e:
        print(f"YouTube ducking skipped: {e}")

    # ── Listen — status shown in current language ─────────────────────────────
    try:
        SetAssistantStatus(language_manager.get_status("listening"))
        Query = SpeechRecognition()
    except SpeechRecognitionError as e:
        error_message = str(e)
        SetMicrophoneStatus("False")
        ShowTextToScreen(f"{Assistantname} : {error_message}")
        SetAssistantStatus("Available...")
        logger.log_interaction(
            query="", decision=[], execution_time=time.time() - start_time,
            apis_used=[], success=False, error_message=error_message
        )
        print(f"Speech recognition failed: {error_message}")
        return False
    finally:
        try:
            from Backend.YouTubeController import yt_controller
            yt_controller.restore_volume()
        except Exception as e:
            print(f"YouTube volume restore skipped: {e}")

    # ── Log detected language ─────────────────────────────────────────────────
    print(f"\n[Language] {language_manager.get_current_language_name()} "
          f"({language_manager.get_current_language().upper()})")

    ShowTextToScreen(f"{Username} : {Query}")
    SetAssistantStatus(language_manager.get_status("thinking"))

    # ── Decision making ───────────────────────────────────────────────────────
    if COMPARISON_MODE:
        try:
            cohere_start    = time.time()
            CohereDec       = FirstlayerDMM(Query)
            cohere_time     = time.time() - cohere_start

            pattern_start   = time.time()
            PatternDecision = pattern_matcher.decide(Query)
            pattern_time    = time.time() - pattern_start

            Decision        = CohereDec
            decision_time   = cohere_time
            decisions_match = set(CohereDec) == set(PatternDecision)

            logger.log_comparison(
                query=Query,
                cohere_decision=CohereDec,
                pattern_decision=PatternDecision,
                cohere_time=cohere_time,
                pattern_time=pattern_time,
                actual_execution='cohere',
                match_accuracy=decisions_match
            )

            print(f"\n[Comparison]")
            print(f"   Cohere:  {CohereDec} ({cohere_time:.3f}s)")
            print(f"   Pattern: {PatternDecision} ({pattern_time:.3f}s)")
            print(f"   Match:   {'yes' if decisions_match else 'no'}")
            if pattern_time > 0.0001:
                print(f"   Speedup: {cohere_time/pattern_time:.1f}x faster with Pattern\n")
            else:
                print(f"   Pattern was instant (< 0.0001s)\n")

        except Exception as e:
            print(f"[WARN] Comparison mode error: {e}")
            decision_start = time.time()
            Decision       = FirstlayerDMM(Query)
            decision_time  = time.time() - decision_start
    else:
        decision_start = time.time()
        Decision       = FirstlayerDMM(Query)
        decision_time  = time.time() - decision_start

    print(f"\nDecision : {Decision}\n")

    NonLanguageDecision = [
        item for item in Decision if not item.startswith("language ")
    ]
    LanguageMessage = None

    for item in Decision:
        if item.startswith("language "):
            if "english" in item:
                LanguageMessage = language_manager.force_set("en")
            else:
                LanguageMessage = language_manager.force_set("bn")
            print(f"[Language] {LanguageMessage}")

    if LanguageMessage and not NonLanguageDecision:
        ShowTextToScreen(f"{Assistantname} : {LanguageMessage}")
        SetAssistantStatus(language_manager.get_status("answering"))
        TextToSpeech(LanguageMessage)
        return True

    G = any(i for i in Decision if i.startswith("general"))
    R = any(i for i in Decision if i.startswith("realtime"))

    Mearged_query = " and ".join(
        [" ".join(i.split(' ')[1:])
         for i in Decision if i.startswith("general") or i.startswith("realtime")]
    )

    apis_used      = ['cohere']
    response_start = time.time()
    success        = True
    error_message  = None
    automation_feedback = []

    try:
        for queries in Decision:
            if "generate" in queries:
                ImageGenerationQuery = str(queries)
                ImageExecution = True
                apis_used.append('huggingface')

        automation_commands = [
            queries for queries in Decision if IsAutomationCommand(queries)
        ]
        if automation_commands:
            automation_feedback = run(Automation(automation_commands))
            TaskExecution = True
            if automation_feedback and not (G or R):
                ShowTextToScreen(
                    f"{Assistantname} : {' '.join(automation_feedback)}"
                )

        if ImageExecution:
            try:
                require_env("HuggingFaceAPIKey")
                ImagePrompt = ImagePromptFromDecision(ImageGenerationQuery)
                with open(r"Frontend\Files\ImageGeneration.data", "w") as file:
                    file.write(f"{ImagePrompt},True")
                ShowTextToScreen(f"{Assistantname} : Generating image for: {ImagePrompt}")
                p1 = subprocess.Popen(
                    [sys.executable, "-m", "Backend.ImageGeneration"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL, shell=False,
                    text=True, encoding="utf-8", errors="replace"
                )
                subprocesses.append(p1)
                threading.Thread(
                    target=WatchImageGenerationProcess,
                    args=(p1,),
                    daemon=True
                ).start()
            except Exception as e:
                print(f"Error starting ImageGeneration.py: {e}")
                success       = False
                error_message = str(e)
                ShowTextToScreen(f"{Assistantname} : {error_message}")

        if G and R:
            SetAssistantStatus(language_manager.get_status("searching"))
            Answer = RealtimeSearchEngine(QueryModifier(Mearged_query))
            apis_used.extend(['groq', 'serper'])
            ShowTextToScreen(f"{Assistantname} : {Answer}")

            response_time = time.time() - response_start
            tts_start     = time.time()
            SetAssistantStatus(language_manager.get_status("answering"))
            TextToSpeech(Answer)

            tts_time   = time.time() - tts_start
            total_time = time.time() - start_time
            logger.log_interaction(
                query=Query, decision=Decision,
                execution_time=total_time, apis_used=apis_used,
                success=success, error_message=error_message,
                decision_time=decision_time,
                response_generation_time=response_time, tts_time=tts_time
            )
            return True

        else:
            for Queries in Decision:

                if "general" in Queries:
                    SetAssistantStatus(language_manager.get_status("thinking"))
                    QueryFinal = Queries.replace("general ", "")
                    Answer     = ChatBot(QueryModifier(QueryFinal))
                    apis_used.append('groq')
                    ShowTextToScreen(f"{Assistantname} : {Answer}")

                    response_time = time.time() - response_start
                    tts_start     = time.time()
                    SetAssistantStatus(language_manager.get_status("answering"))
                    TextToSpeech(Answer)

                    tts_time   = time.time() - tts_start
                    total_time = time.time() - start_time
                    logger.log_interaction(
                        query=Query, decision=Decision,
                        execution_time=total_time, apis_used=apis_used,
                        success=success, error_message=error_message,
                        decision_time=decision_time,
                        response_generation_time=response_time, tts_time=tts_time
                    )
                    return True

                elif "realtime" in Queries:
                    SetAssistantStatus(language_manager.get_status("searching"))
                    QueryFinal = Queries.replace("realtime ", "")
                    Answer     = RealtimeSearchEngine(QueryModifier(QueryFinal))
                    apis_used.extend(['groq', 'serper'])
                    ShowTextToScreen(f"{Assistantname} : {Answer}")

                    response_time = time.time() - response_start
                    tts_start     = time.time()
                    SetAssistantStatus(language_manager.get_status("answering"))
                    TextToSpeech(Answer)

                    tts_time   = time.time() - tts_start
                    total_time = time.time() - start_time
                    logger.log_interaction(
                        query=Query, decision=Decision,
                        execution_time=total_time, apis_used=apis_used,
                        success=success, error_message=error_message,
                        decision_time=decision_time,
                        response_generation_time=response_time, tts_time=tts_time
                    )
                    return True

                elif Queries.startswith("content "):
                    SetAssistantStatus(language_manager.get_status("thinking"))
                    QueryFinal = Queries.replace("content ", "", 1)
                    ContentPrompt = (
                        "Write this as complete polished content. "
                        "Return only the requested content, no extra notes: "
                        f"{QueryFinal}"
                    )
                    Answer = ChatBot(QueryModifier(ContentPrompt))
                    apis_used.append('groq')
                    ShowTextToScreen(f"{Assistantname} : {Answer}")

                    response_time = time.time() - response_start
                    tts_start = time.time()
                    SetAssistantStatus(language_manager.get_status("answering"))
                    TextToSpeech(ContentSpeechText(Answer))
                    tts_time = time.time() - tts_start
                    total_time = time.time() - start_time
                    logger.log_interaction(
                        query=Query, decision=Decision,
                        execution_time=total_time, apis_used=apis_used,
                        success=success, error_message=error_message,
                        decision_time=decision_time,
                        response_generation_time=response_time,
                        tts_time=tts_time
                    )
                    SetAssistantStatus("Available...")
                    return True

                elif "exit" in Queries:
                    QueryFinal = "ঠিক আছে, বিদায়!" if language_manager.is_bangla() else "Okay, Bye!"
                    Answer     = ChatBot(QueryModifier(QueryFinal))
                    ShowTextToScreen(f"{Assistantname} : {Answer}")
                    SetAssistantStatus(language_manager.get_status("answering"))
                    sleep(0.5)

                    response_time = time.time() - response_start
                    tts_start     = time.time()
                    TextToSpeech(Answer)

                    tts_time   = time.time() - tts_start
                    total_time = time.time() - start_time
                    logger.log_interaction(
                        query=Query, decision=Decision,
                        execution_time=total_time, apis_used=apis_used,
                        success=True, decision_time=decision_time,
                        response_generation_time=response_time, tts_time=tts_time
                    )
                    QApplication.instance().quit()
                    return True
                elif Queries.startswith("language "):
                    continue

            if TaskExecution and not (G or R):
                total_time = time.time() - start_time
                logger.log_interaction(
                    query=Query, decision=Decision,
                    execution_time=total_time, apis_used=apis_used,
                    success=success, error_message=error_message,
                    decision_time=decision_time,
                    response_generation_time=time.time() - response_start,
                    tts_time=0
                )
                return True

    except Exception as e:
        success       = False
        error_message = str(e)
        total_time    = time.time() - start_time
        logger.log_interaction(
            query=Query, decision=Decision,
            execution_time=total_time, apis_used=apis_used,
            success=success, error_message=error_message,
            decision_time=decision_time,
            response_generation_time=0, tts_time=0
        )
        print(f"[ERROR] Error in MainExecution: {e}")
        import traceback
        traceback.print_exc()

def PrepareTextQuery(TextQuery):
    TextQuery = TextQuery.strip()
    detected_lang = language_manager.detect_and_set(TextQuery)
    print(f"\n[TextInput] Raw text: '{TextQuery}'")
    print(
        f"[TextInput] Detected: {detected_lang.upper()} "
        f"| Voice: {language_manager.get_tts_voice()}"
    )

    if detected_lang == "en":
        return QueryModifier(TextQuery)

    SetAssistantStatus(language_manager.get_status("translating"))
    english_text = TranslateToEnglish(TextQuery)
    print(f"[TextInput] Translated to EN: '{english_text}'")
    return QueryModifier(english_text)

def TextExecution(TextQuery):
    global SpeechRecognition

    Query = PrepareTextQuery(TextQuery)
    original_speech_recognition = SpeechRecognition
    SpeechRecognition = lambda: Query

    try:
        return MainExecution()
    finally:
        SpeechRecognition = original_speech_recognition

def ImagePromptFromDecision(DecisionQuery):
    Prompt = DecisionQuery.strip()
    for Prefix in ("generate image", "generate"):
        if Prompt.lower().startswith(Prefix):
            Prompt = Prompt[len(Prefix):].strip()
            break
    return Prompt or DecisionQuery.strip()

def WatchImageGenerationProcess(Process):
    stdout, stderr = Process.communicate()

    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)

    if Process.returncode == 0:
        ShowTextToScreen(f"{Assistantname} : Image generated.")
    else:
        details = (stderr or stdout or "Unknown image generation error.").strip()
        ShowTextToScreen(f"{Assistantname} : Image generation failed: {details[-500:]}")
    SetAssistantStatus("Available...")

def FirstThread():
    while True:
        try:
            HandleDueReminders()
            TextQuery = GetTextQuery().strip()
            if TextQuery:
                ClearTextQuery()
                SetMicrophoneStatus("False")
                TextExecution(TextQuery)
                continue

            CurrentStatus = GetMicrophoneStatus()
            if CurrentStatus == "True":
                MainExecution()
            else:
                AIStatus = GetAssistantStatus()
                if "Available..." in AIStatus:
                    sleep(0.1)
                else:
                    SetAssistantStatus("Available...")
        except Exception as e:
            print(f"[ERROR] Thread error: {e}")
            sleep(1)

def SecondThread():
    GraphicalUserInterface()

def HandleDueReminders():
    try:
        due_reminders = pop_due_reminders()
    except Exception as e:
        print(f"Reminder check failed: {e}")
        return

    for reminder in due_reminders:
        message = reminder.get("message", "your reminder")
        alert = f"Reminder: {message}"
        ShowTextToScreen(f"{Assistantname} : {alert}")
        SetAssistantStatus("Reminder...")
        TextToSpeech(alert)

if __name__ == "__main__":
    InitialExecution()
    thread2 = threading.Thread(target=FirstThread, daemon=True)
    thread2.start()
    SecondThread()
