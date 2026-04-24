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
    GetAssistantStatus)
from Backend.Model import FirstlayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from Backend.PerformanceLogger import logger
from Backend.SimpleDecisionMaker import SimplePatternMatcher
from Backend.LanguageManager import language_manager
from dotenv import dotenv_values
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import time
import os

env_vars      = dotenv_values(".env")
Username      = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. What can I assist you with?'''
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search",
             "youtube search", "youtube control"]

pattern_matcher = SimplePatternMatcher()
COMPARISON_MODE = True

def ShowDefaultChatIfNotChats():
    try:
        File    = open(r'Data\ChatLog.json', "r", encoding='utf-8')
        content = File.read()
        File.close()
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
        print("⚠️ Chatlog.json corrupted. Resetting...")
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
        print("✅ Mamur Beta initialized successfully!")
        print(f"🌐 Default language: {language_manager.get_current_language_name()}")
    except Exception as e:
        print(f"❌ Initialization error: {e}")

InitialExecution()

def MainExecution():

    start_time           = time.time()
    TaskExecution        = False
    ImageExecution       = False
    ImageGenerationQuery = ""

    # ── Duck YouTube volume BEFORE mic opens ──────────────────────────────────
    try:
        from Backend.YouTubeController import yt_controller
        yt_controller.duck_volume(duck_to=8)
    except Exception:
        pass

    # ── Listen — status shown in current language ─────────────────────────────
    SetAssistantStatus(language_manager.get_status("listening"))
    Query = SpeechRecognition()

    # ── Restore YouTube volume AFTER query captured ───────────────────────────
    try:
        from Backend.YouTubeController import yt_controller
        yt_controller.restore_volume()
    except Exception:
        pass

    # ── Log detected language ─────────────────────────────────────────────────
    print(f"\n🌐 Language: {language_manager.get_current_language_name()} "
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

            print(f"\n🔬 COMPARISON:")
            print(f"   Cohere:  {CohereDec} ({cohere_time:.3f}s)")
            print(f"   Pattern: {PatternDecision} ({pattern_time:.3f}s)")
            print(f"   Match:   {'✅' if decisions_match else '❌'}")
            if pattern_time > 0.0001:
                print(f"   Speedup: {cohere_time/pattern_time:.1f}x faster with Pattern\n")
            else:
                print(f"   Pattern was instant (< 0.0001s)\n")

        except Exception as e:
            print(f"⚠️ Comparison mode error: {e}")
            decision_start = time.time()
            Decision       = FirstlayerDMM(Query)
            decision_time  = time.time() - decision_start
    else:
        decision_start = time.time()
        Decision       = FirstlayerDMM(Query)
        decision_time  = time.time() - decision_start

    print(f"\nDecision : {Decision}\n")

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

    try:
        for queries in Decision:
            if "generate" in queries:
                ImageGenerationQuery = str(queries)
                ImageExecution = True
                apis_used.append('huggingface')

        for queries in Decision:
            if not TaskExecution:
                if any(func in queries for func in Functions):
                    run(Automation(list(Decision)))
                    TaskExecution = True

        if ImageExecution:
            with open(r"Frontend\Files\ImageGeneration.data", "w") as file:
                file.write(f"{ImageGenerationQuery},True")
            try:
                p1 = subprocess.Popen(
                    ['python', r'Backend\ImageGeneration.py'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE, shell=False
                )
                subprocesses.append(p1)
            except Exception as e:
                print(f"Error starting ImageGeneration.py: {e}")
                success       = False
                error_message = str(e)

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
                elif "language" in Queries:
                    if "english" in Queries:
                        msg = language_manager.force_set("en")
                    else:
                        msg = language_manager.force_set("bn")
                    ShowTextToScreen(f"{Assistantname} : {msg}")
                    SetAssistantStatus(language_manager.get_status("answering"))
                    TextToSpeech(msg)
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
        print(f"❌ Error in MainExecution: {e}")
        import traceback
        traceback.print_exc()

def FirstThread():
    while True:
        try:
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
            print(f"❌ Thread error: {e}")
            sleep(1)

def SecondThread():
    GraphicalUserInterface()

if __name__ == "__main__":
    thread2 = threading.Thread(target=FirstThread, daemon=True)
    thread2.start()
    SecondThread()