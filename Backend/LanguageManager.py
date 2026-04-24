"""
LanguageManager.py  —  Backend/LanguageManager.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bilingual (Bangla / English) language manager for Mamur Beta.

Default language is BANGLA. Switches to English only when English
is clearly detected. This is ideal when the primary user speaks Bangla.
"""

import logging
from typing import Literal

# ── Optional: langdetect ──────────────────────────────────────────────────────
try:
    from langdetect import detect, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    DetectorFactory.seed = 42
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

log = logging.getLogger("LanguageManager")

# ─────────────────────────────────────────────────────────────────────────────
#  Language configuration
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_CONFIG = {
    "en": {
        "name"              : "English",
        "recognition_lang"  : "en-US",
        "tts_voice"         : "en-CA-LiamNeural",
        "reply_instruction" : (
            "*** Always reply in English only. "
            "Do not use Bangla in your response. ***"
        ),
        "listening_status"  : "Listening...",
        "thinking_status"   : "Thinking...",
        "searching_status"  : "Searching...",
        "answering_status"  : "Answering...",
        "translating_status": "Translating...",
    },
    "bn": {
        "name"              : "বাংলা",
        "recognition_lang"  : "bn-BD",
        "tts_voice"         : "bn-IN-TanishaaNeural",
        "reply_instruction" : (
            "*** সবসময় বাংলায় উত্তর দাও। "
            "ইংরেজিতে উত্তর দেওয়া যাবে না। "
            "Always reply in Bangla (Bengali) only. "
            "Do not reply in English under any circumstance. ***"
        ),
        "listening_status"  : "শুনছি...",
        "thinking_status"   : "ভাবছি...",
        "searching_status"  : "খুঁজছি...",
        "answering_status"  : "বলছি...",
        "translating_status": "অনুবাদ করছি...",
    }
}

# Bangla Unicode block: U+0980 → U+09FF
_BANGLA_START = 0x0980
_BANGLA_END   = 0x09FF

# Common romanized Bangla words (typed/spoken in Latin script by Bangladeshis)
# If the transcript is all-Latin but contains these words → treat as Bangla
_ROMANIZED_BANGLA_KEYWORDS = {
    "ami", "tumi", "amar", "tomar", "apni", "apnar", "kemon", "acho",
    "achi", "bhalo", "kharap", "ki", "kি", "ke", "kothay", "kobe",
    "keno", "hya", "na", "thik", "ache", "hobe", "dao", "bolo",
    "jao", "eso", "ek", "dui", "tin", "char", "panch", "mamur",
    "bolো", "janো", "dekho", "shono", "boro", "choto", "sundor",
    "valo", "valo achi", "khaici", "khabo", "jabo", "asbo", "korbo",
    "bolbe", "janbe", "dekhbe", "shunbe", "boro", "chotto",
    "dada", "bhai", "apu", "amma", "abbu", "chacha", "mama",
    "tomake", "amake", "apnake", "tar", "tader", "amader", "tোmader",
    "ektu", "onek", "khub", "aro", "abার", "kintu", "tahole",
    "jodi", "taহole", "ebং", "othoba", "nahole", "kারণ",
}


# ─────────────────────────────────────────────────────────────────────────────
#  LanguageManager class
# ─────────────────────────────────────────────────────────────────────────────

class LanguageManager:
    """
    Singleton language manager.
    Starts in Bangla by default. Switches to English only when
    clearly English text is detected. Handles both native Bangla
    script and romanized Bangla (Latin letters).
    """

    def __init__(self, default_language: Literal["en", "bn"] = "bn"):
        self._current_language: str  = default_language
        self._previous_language: str = default_language
        log.info(f"LanguageManager ready. Default: {default_language}")

    # ── Detection helpers ─────────────────────────────────────────────────────

    def _bangla_unicode_ratio(self, text: str) -> float:
        """Fraction of alphabetic chars that are Bangla Unicode."""
        alpha  = [ch for ch in text if ch.isalpha()]
        if not alpha:
            return 0.0
        bangla = [ch for ch in alpha
                  if _BANGLA_START <= ord(ch) <= _BANGLA_END]
        return len(bangla) / len(alpha)

    def _is_romanized_bangla(self, text: str) -> bool:
        """
        Check if a Latin-script text is romanized Bangla.
        Matches against common Bangla words written in English letters.
        """
        words = set(text.lower().split())
        matches = words & _ROMANIZED_BANGLA_KEYWORDS
        # If 2+ known Bangla words found → likely romanized Bangla
        return len(matches) >= 2

    def detect_language(self, text: str) -> Literal["en", "bn"]:
        """
        Detect whether text is Bangla or English.

        Priority:
          1. Bangla Unicode script ratio      → most reliable
          2. Romanized Bangla keyword match   → catches Latin-script Bangla
          3. langdetect library               → general fallback
          4. Keep current language            → safe default (stays Bangla)
        """
        if not text or not text.strip():
            return self._current_language

        text_clean = text.strip()

        # ── Step 1: Native Bangla script ──────────────────────────────────
        ratio = self._bangla_unicode_ratio(text_clean)
        if ratio > 0.25:
            log.info(f"Bangla script detected (ratio={ratio:.2f})")
            return "bn"

        # ── Step 2: Romanized Bangla ──────────────────────────────────────
        if self._is_romanized_bangla(text_clean):
            log.info("Romanized Bangla detected via keyword match")
            return "bn"

        # ── Step 3: langdetect ────────────────────────────────────────────
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text_clean)
                log.info(f"langdetect → '{detected}'")
                if detected == "bn":
                    return "bn"
                if detected in ("hi", "ne", "mr") and ratio > 0.05:
                    # Sometimes Bangla is confused with nearby languages
                    return "bn"
                if detected == "en":
                    # Only switch to English if we're confident
                    # (langdetect says 'en' AND no Bangla indicators at all)
                    if ratio == 0.0 and not self._is_romanized_bangla(text_clean):
                        return "en"
                    else:
                        # Has some Bangla indicators — stay Bangla
                        return "bn"
            except LangDetectException:
                pass
            except Exception as e:
                log.warning(f"langdetect error: {e}")

        # ── Step 4: Keep current (defaults to Bangla) ─────────────────────
        log.info(f"No clear detection — keeping: {self._current_language}")
        return self._current_language

    def detect_and_set(self, text: str) -> Literal["en", "bn"]:
        """Detect language of `text` and update the active language."""
        detected = self.detect_language(text)

        if detected != self._current_language:
            self._previous_language = self._current_language
            self._current_language  = detected
            log.info(
                f"🌐 Language: {self._previous_language.upper()} "
                f"→ {detected.upper()}"
            )
        else:
            log.info(f"🌐 Language confirmed: {detected.upper()}")

        return detected

    # ── Getters ───────────────────────────────────────────────────────────────

    def get_current_language(self) -> Literal["en", "bn"]:
        return self._current_language

    def get_current_language_name(self) -> str:
        return LANGUAGE_CONFIG[self._current_language]["name"]

    def get_recognition_lang(self) -> str:
        return LANGUAGE_CONFIG[self._current_language]["recognition_lang"]

    def get_tts_voice(self) -> str:
        return LANGUAGE_CONFIG[self._current_language]["tts_voice"]

    def get_reply_instruction(self) -> str:
        return LANGUAGE_CONFIG[self._current_language]["reply_instruction"]

    def get_status(self, status_key: str) -> str:
        key = f"{status_key}_status"
        return LANGUAGE_CONFIG[self._current_language].get(
            key, status_key.capitalize() + "..."
        )

    def is_bangla(self) -> bool:
        return self._current_language == "bn"

    def is_english(self) -> bool:
        return self._current_language == "en"

    def force_set(self, lang: Literal["en", "bn"]) -> str:
        """Manually override language from a voice command."""
        if lang not in ("en", "bn"):
            return f"Unknown language '{lang}'."
        self._previous_language = self._current_language
        self._current_language  = lang
        log.info(f"Language manually set to: {lang.upper()}")
        if lang == "bn":
            return "ঠিক আছে, এখন থেকে বাংলায় কথা বলব।"
        return "Alright, switching to English mode."

    def __repr__(self):
        return (
            f"LanguageManager("
            f"lang='{self._current_language}', "
            f"voice='{self.get_tts_voice()}')"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Singleton — import this in other Backend files using:
#  from .LanguageManager import language_manager
# ─────────────────────────────────────────────────────────────────────────────
language_manager = LanguageManager(default_language="bn")