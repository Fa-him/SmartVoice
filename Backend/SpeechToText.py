from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from .LanguageManager import language_manager
import os
import mtranslate as mt

current_dir = os.getcwd()

# ── HTML — starts with bn-BD so Chrome captures native Bangla script ──────────
HtmlCode = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Speech Recognition</title>
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end"   onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <script>
        const output = document.getElementById('output');
        let recognition;
        let currentLang = 'bn-BD';

        function setLang(lang) {
            currentLang = lang;
            if (recognition) {
                recognition.onend = null;
                recognition.stop();
                setTimeout(startRecognition, 300);
            }
        }

        function startRecognition() {
            recognition = new webkitSpeechRecognition() || new SpeechRecognition();
            recognition.lang = currentLang;
            recognition.continuous = true;
            recognition.interimResults = false;

            recognition.onresult = function(event) {
                const transcript = event.results[event.results.length - 1][0].transcript;
                output.textContent += transcript;
            };

            recognition.onend = function() {
                recognition.lang = currentLang;
                recognition.start();
            };

            recognition.onerror = function(event) {
                if (event.error !== 'no-speech') {
                    console.log('Error: ' + event.error);
                }
            };

            recognition.start();
        }

        function stopRecognition() {
            if (recognition) {
                recognition.onend = null;
                recognition.stop();
            }
            output.innerHTML = "";
        }
    </script>
</body>
</html>'''

# Write HTML file
html_path = os.path.join(current_dir, "Data", "Voice.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(HtmlCode)

Link = f"{current_dir}/Data/Voice.html"

# ── Chrome WebDriver ──────────────────────────────────────────────────────────
chrome_options = Options()
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.142.86 Safari/537.36"
)
chrome_options.add_argument("--use-fake-ui-for-media-stream")
chrome_options.add_argument("--use-fake-device-for-media-stream")
chrome_options.add_argument("--headless=new")

service = Service(ChromeDriverManager().install())
driver  = webdriver.Chrome(service=service, options=chrome_options)

TempDirPath = rf"{current_dir}/Frontend/Files"


# ── Helpers ───────────────────────────────────────────────────────────────────

def SetAssistantStatus(Status):
    with open(rf'{TempDirPath}/Status.data', "w", encoding="utf-8") as file:
        file.write(Status)

def QueryModifier(Query):
    new_query   = Query.lower().strip()
    query_words = new_query.split()
    if not query_words:
        return Query

    question_words = [
        "how", "what", "who", "where", "when", "why", "which",
        "whose", "whom", "can you", "what's", "where's", "how's",
        "কি", "কী", "কে", "কোথায়", "কখন", "কেন", "কীভাবে", "কিভাবে"
    ]

    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()

def TranslateToEnglish(Text: str) -> str:
    """Translate any language to English for the AI pipeline."""
    try:
        return mt.translate(Text, "en", "auto").capitalize()
    except Exception as e:
        print(f"[SpeechToText] Translation error: {e}")
        return Text

def _set_browser_lang(lang_code: str):
    """Update the browser recognizer language without page reload."""
    try:
        driver.execute_script(f"setLang('{lang_code}');")
    except Exception:
        pass


# ── Main function ─────────────────────────────────────────────────────────────

def SpeechRecognition() -> str:
    """
    Capture voice and return an English query string for the AI.

    - Browser starts in bn-BD so Bangla speech gives real Unicode script
    - After capturing, LanguageManager detects the language
    - If Bangla → translates to English for the AI, but keeps lang='bn'
      so Chatbot and TTS respond in Bangla
    - If English → uses text as-is, sets lang='en'
    """
    driver.get("file:///" + Link)

    # Set browser to current language (bn-BD by default)
    _set_browser_lang(language_manager.get_recognition_lang())

    driver.find_element(by=By.ID, value="start").click()

    while True:
        try:
            Text = driver.find_element(by=By.ID, value="output").text

            if Text:
                driver.find_element(by=By.ID, value="end").click()

                # ── Detect language ───────────────────────────────────────
                detected_lang = language_manager.detect_and_set(Text)

                # DEBUG — remove after confirming it works
                print(f"\n🔍 Raw speech: '{Text}'")
                print(f"🌐 Detected: {detected_lang.upper()} "
                      f"| Voice: {language_manager.get_tts_voice()}")

                # ── Update browser for next call ──────────────────────────
                _set_browser_lang(language_manager.get_recognition_lang())

                # ── Process ───────────────────────────────────────────────
                if detected_lang == "en":
                    return QueryModifier(Text)
                else:
                    # Bangla → translate to English for Model.py
                    # AI will reply in Bangla due to system prompt
                    SetAssistantStatus(
                        language_manager.get_status("translating")
                    )
                    english_text = TranslateToEnglish(Text)
                    print(f"📝 Translated to EN: '{english_text}'")
                    return QueryModifier(english_text)

        except Exception:
            pass


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Bilingual test — speak Bangla or English.\n")
    while True:
        text = SpeechRecognition()
        print(f"→ {text}\n")