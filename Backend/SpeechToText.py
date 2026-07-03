import atexit
import time
from pathlib import Path

import mtranslate as mt
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from Backend.Config import ROOT_DIR, get_env
from Backend.LanguageManager import language_manager


class SpeechRecognitionError(RuntimeError):
    """Raised when browser-based speech recognition cannot complete."""


DATA_DIR = ROOT_DIR / "Data"
TEMP_DIR = ROOT_DIR / "Frontend" / "Files"
VOICE_HTML_PATH = DATA_DIR / "Voice.html"

_driver = None


HTML_CODE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>SmartVoice Speech Recognition</title>
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end" onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <p id="error"></p>
    <script>
        const output = document.getElementById('output');
        const errorBox = document.getElementById('error');
        const SpeechRecognitionClass =
            window.SpeechRecognition || window.webkitSpeechRecognition;

        let recognition = null;
        let currentLang = 'bn-BD';
        let shouldListen = false;

        function setLang(lang) {
            currentLang = lang;
            if (recognition && shouldListen) {
                stopRecognition(false);
                setTimeout(startRecognition, 300);
            }
        }

        function resetOutput() {
            output.textContent = '';
            errorBox.textContent = '';
        }

        function startRecognition() {
            if (!SpeechRecognitionClass) {
                errorBox.textContent = 'speech-api-not-supported';
                return;
            }

            shouldListen = true;
            recognition = new SpeechRecognitionClass();
            recognition.lang = currentLang;
            recognition.continuous = true;
            recognition.interimResults = false;

            recognition.onresult = function(event) {
                const result = event.results[event.results.length - 1];
                if (result && result[0] && result[0].transcript) {
                    const transcript = result[0].transcript.trim();
                    output.textContent = (output.textContent + ' ' + transcript).trim();
                }
            };

            recognition.onerror = function(event) {
                errorBox.textContent = event.error || 'unknown-speech-error';
            };

            recognition.onend = function() {
                if (shouldListen) {
                    setTimeout(startRecognition, 300);
                }
            };

            try {
                resetOutput();
                recognition.start();
            } catch (error) {
                errorBox.textContent = error.message || 'speech-start-failed';
            }
        }

        function stopRecognition(clearOutput = false) {
            shouldListen = false;
            if (recognition) {
                recognition.onend = null;
                recognition.stop();
            }
            if (clearOutput) {
                resetOutput();
            }
        }
    </script>
</body>
</html>"""


def _bool_env(name: str, default: bool) -> bool:
    value = get_env(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    value = get_env(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _write_voice_html() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_HTML_PATH.write_text(HTML_CODE, encoding="utf-8")


def _build_chrome_options() -> Options:
    options = Options()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--allow-file-access-from-files")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=420,260")

    if _bool_env("SpeechRecognitionAutoGrantMic", True):
        options.add_argument("--use-fake-ui-for-media-stream")

    if _bool_env("SpeechRecognitionUseFakeMic", False):
        options.add_argument("--use-fake-device-for-media-stream")

    if _bool_env("SpeechRecognitionHeadless", False):
        options.add_argument("--headless=new")

    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options


def _build_driver():
    try:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=_build_chrome_options())
    except Exception as e:
        raise SpeechRecognitionError(
            "Could not start Chrome speech recognition. "
            "Check that Chrome is installed and webdriver-manager can access a matching driver."
        ) from e


def _get_driver():
    global _driver
    if _driver is not None:
        try:
            _driver.current_url
            return _driver
        except WebDriverException:
            _driver = None

    _driver = _build_driver()
    return _driver


def close_speech_driver() -> None:
    global _driver
    if _driver is None:
        return
    try:
        _driver.quit()
    except Exception:
        pass
    finally:
        _driver = None


atexit.register(close_speech_driver)


def SetAssistantStatus(Status):
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    with open(TEMP_DIR / "Status.data", "w", encoding="utf-8") as file:
        file.write(Status)


def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    if not query_words:
        return Query

    question_words = [
        "how", "what", "who", "where", "when", "why", "which",
        "whose", "whom", "can you", "what's", "where's", "how's",
        "ki", "ke", "kothay", "kokhon", "keno", "kibhabe",
    ]

    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in [".", "?", "!"]:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in [".", "?", "!"]:
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


def _set_browser_lang(driver, lang_code: str) -> None:
    try:
        driver.execute_script("setLang(arguments[0]);", lang_code)
    except Exception as e:
        raise SpeechRecognitionError(
            f"Could not set speech recognition language to {lang_code}."
        ) from e


def _stop_recognition(driver) -> None:
    try:
        driver.execute_script("stopRecognition(false);")
    except Exception:
        pass


def _capture_transcript(timeout_seconds: float) -> str:
    _write_voice_html()
    driver = _get_driver()

    try:
        driver.get(Path(VOICE_HTML_PATH).resolve().as_uri())
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "start")))

        _set_browser_lang(driver, language_manager.get_recognition_lang())
        driver.find_element(By.ID, "start").click()

        deadline = time.monotonic() + timeout_seconds
        last_error = ""
        while time.monotonic() < deadline:
            text = driver.find_element(By.ID, "output").text.strip()
            if text:
                return text

            error_text = driver.find_element(By.ID, "error").text.strip()
            if error_text and error_text != last_error:
                last_error = error_text
                if error_text not in {"no-speech"}:
                    raise SpeechRecognitionError(
                        f"Browser speech recognition error: {error_text}"
                    )

            time.sleep(_float_env("SpeechRecognitionPollSeconds", 0.2))

        raise SpeechRecognitionError(
            f"No speech detected within {int(timeout_seconds)} seconds."
        )

    except SpeechRecognitionError:
        raise
    except WebDriverException as e:
        close_speech_driver()
        raise SpeechRecognitionError(
            "Chrome speech recognition became unavailable. "
            "Please try the microphone again."
        ) from e
    except Exception as e:
        raise SpeechRecognitionError(
            f"Unexpected speech recognition error: {e}"
        ) from e
    finally:
        _stop_recognition(driver)


def SpeechRecognition(timeout_seconds: float | None = None) -> str:
    """
    Capture voice and return an English query string for the AI.

    The browser is created lazily on the first call. Bangla input is translated
    to English for intent routing while the active response language stays Bangla.
    """
    timeout = timeout_seconds or _float_env("SpeechRecognitionTimeoutSeconds", 20)
    Text = _capture_transcript(timeout)

    detected_lang = language_manager.detect_and_set(Text)

    print(f"\n[SpeechToText] Raw speech: '{Text}'")
    print(
        f"[SpeechToText] Detected: {detected_lang.upper()} "
        f"| Voice: {language_manager.get_tts_voice()}"
    )

    if detected_lang == "en":
        return QueryModifier(Text)

    SetAssistantStatus(language_manager.get_status("translating"))
    english_text = TranslateToEnglish(Text)
    print(f"[SpeechToText] Translated to EN: '{english_text}'")
    return QueryModifier(english_text)


if __name__ == "__main__":
    print("Bilingual test - speak Bangla or English.\n")
    while True:
        try:
            text = SpeechRecognition()
            print(f"-> {text}\n")
        except SpeechRecognitionError as e:
            print(f"Speech recognition failed: {e}\n")
