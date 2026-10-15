# SmartVoice

SmartVoice is a bilingual Windows desktop assistant prototype. It uses a PyQt5 GUI, voice input, AI intent routing, task automation, realtime search, image generation, and text-to-speech to answer questions and act on voice commands.

Important: the current implementation is cloud-assisted, not fully offline/private. It can call services such as Chrome Web Speech, Cohere, Groq, Serper, Hugging Face, Microsoft Edge TTS, and translation APIs.

## What It Can Do

- Listen for Bangla or English voice commands.
- Detect the active language and respond with matching TTS.
- Route commands into chat, realtime search, automation, image generation, language switching, or exit.
- Set local reminders and announce them when they are due.
- Open/close apps and websites, search Google/YouTube, play YouTube media, control YouTube playback, and control system volume.
- Generate images through Hugging Face and save them in `Data`.
- Log performance and comparison metrics for research notes.

## Requirements

- Windows
- Python 3.10 or newer recommended
- Google Chrome installed
- A working microphone
- API keys for the services you want to use

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r Requirements.txt
```

On first run, SmartVoice opens a setup window and asks for the user's name, assistant name, API keys, image settings, and speech-recognition options. It saves those values locally in `.env`, so each installed user can use their own API keys without editing files manually.

For developer setup, you can still copy `.env.example` to `.env` and edit it by hand. If `.env` is missing or still contains placeholder keys like `your_groq_api_key`, the setup window appears automatically.

Speech recognition uses Chrome through Selenium. For real microphone input, keep `SpeechRecognitionHeadless=False` and `SpeechRecognitionUseFakeMic=False` in `.env`.

Image generation uses Hugging Face Inference Providers through `huggingface_hub`. The default model is `black-forest-labs/FLUX.1-schnell`; change `HuggingFaceImageModel` or `HuggingFaceProvider` in `.env` if your Hugging Face account/provider access requires a different route.

## Run 

```powershell
.\.venv\Scripts\activate
python main.py
```

## Production-Style Use

SmartVoice is ready for a first-run configuration flow: package the app, ship it without `.env`, and let each customer enter their own API keys during the first launch. The generated `.env` stays on that customer's machine and is ignored by git.

## Build Windows Release

Install build tooling once:

```powershell
.\tools\build_windows.ps1 -InstallBuildDeps
```

Build the app:

```powershell
.\tools\build_windows.ps1
```

The executable folder is created at `dist\SmartVoice`.

To build a customer installer, install Inno Setup 6 and run:

```powershell
.\tools\build_installer.ps1
```

The installer is created under `dist\installer`. It installs per user under LocalAppData, creates writable `Data` and `Frontend\Files` folders, and launches the first-run setup wizard when `.env` is missing.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Reminder Examples

SmartVoice can set reminders from phrases like:

- `remind me in 10 minutes to stretch`
- `set a reminder at 9:00 PM tomorrow to check the oven`
- `reminder 10:00 AM 20th September job interview`

## Useful Files

- `main.py` - main assistant loop and routing
- `Frontend/GUI.py` - PyQt5 desktop interface
- `Backend/Model.py` - Cohere-based intent classification
- `Backend/Chatbot.py` - general Groq chat responses
- `Backend/RealtimeSearchEngine.py` - Serper search plus Groq answers
- `Backend/SpeechToText.py` - Selenium/Chrome speech recognition bridge
- `Backend/TextToSpeech.py` - Edge TTS speech output
- `Backend/Automation.py` - app, website, search, content, media, and system automation
- `Backend/ReminderManager.py` - local reminder parsing, storage, and due-reminder checks
- `Backend/YouTubeController.py` - Selenium YouTube playback and controls used by `play` and `youtube control` commands
- `Backend/PerformanceLogger.py` - runtime metrics and paper-ready exports

## Runtime Data

SmartVoice writes generated state, reminders, logs, speech audio, images, and chat files under `Data` and `Frontend/Files`. These are local runtime artifacts and should not be treated as source code.

If these files are already tracked in git, remove them from the index once with `git rm --cached -- <path>` while keeping the local files on disk.

## Troubleshooting

- If speech recognition fails, check Chrome, microphone permissions, and network access.
- If the assistant never hears you, increase `SpeechRecognitionTimeoutSeconds` or check that Chrome is allowed to use the microphone.
- If chat/search/image/TTS fails, check the related API key in `.env`.
- If image generation fails with provider, DNS, billing, or model-access errors, try a different `HuggingFaceImageModel`/`HuggingFaceProvider` or verify Hugging Face Inference Provider access for your account.
- If a fresh install fails on imports, reinstall dependencies with `python -m pip install -r Requirements.txt`.
