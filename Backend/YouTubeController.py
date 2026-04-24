"""
YouTubeController.py  —  Backend/YouTubeController.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Standalone YouTube playback controller for Mamur Beta.
Controls YouTube via Selenium — no window focus needed.

Supported voice commands (routed via 'youtube control' prefix):
  play <song>              → launch(query)
  pause / resume           → pause() / play()
  fullscreen               → toggle_fullscreen()
  captions on/off          → toggle_captions()
  theater mode             → toggle_theater()
  ambient mode             → toggle_ambient()
  autoplay on/off          → toggle_autoplay()
  speed 1.5 / slow down    → set_speed(rate)
  sleep timer 30           → set_sleep_timer(minutes)
  cancel timer             → cancel_sleep_timer()
  skip forward/back        → skip(seconds)
  mute / unmute            → toggle_mute()
  volume 70                → set_volume(percent)
  next / previous video    → next_video() / prev_video()
  close youtube            → close()
  youtube status           → get_status()

Audio ducking (called by main.py):
  duck_volume(duck_to)     → Lower YT volume while mic is listening
  restore_volume()         → Restore volume after speech captured
"""

import time
import threading
import re
import logging
from typing import Optional

# ── Selenium imports ──────────────────────────────────────────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        WebDriverException,
        NoSuchElementException,
        TimeoutException,
        JavascriptException,
        SessionNotCreatedException,
        NoSuchWindowException,
    )
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[YouTubeController] %(levelname)s: %(message)s"
)
log = logging.getLogger("YouTubeController")


# ─────────────────────────────────────────────────────────────────────────────
#  Custom Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class YTControllerError(Exception):
    """Base exception for YouTubeController."""
    pass

class YTNotLaunchedError(YTControllerError):
    """Raised when a control method is called before launch()."""
    pass

class YTBrowserClosedError(YTControllerError):
    """Raised when the browser window was closed externally."""
    pass

class YTNoVideoError(YTControllerError):
    """Raised when no video element is found on the page."""
    pass

class YTSeleniumMissingError(YTControllerError):
    """Raised when Selenium / webdriver-manager is not installed."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  YouTubePlayer  (main class)
# ─────────────────────────────────────────────────────────────────────────────

class YouTubePlayer:
    """
    Controls a YouTube video running in a Selenium-managed Chrome window.
    Designed as a singleton — use the module-level `yt_controller` instance.
    """

    # ── YouTube DOM selectors ─────────────────────────────────────────────────
    _SEL = {
        "video"         : "video.html5-main-video",
        "play_btn"      : ".ytp-play-button",
        "fullscreen_btn": ".ytp-fullscreen-button",
        "captions_btn"  : ".ytp-subtitles-button",
        "theater_btn"   : ".ytp-size-button",
        "autoplay_btn"  : ".ytp-autonav-toggle-button",
        "mute_btn"      : ".ytp-mute-button",
        "settings_btn"  : ".ytp-settings-button",
        "next_btn"      : ".ytp-next-button",
        "first_result"  : "ytd-video-renderer a#video-title",
    }

    # ── Speed display names ───────────────────────────────────────────────────
    _SPEED_LABELS = {
        0.25: "0.25", 0.5: "0.5", 0.75: "0.75",
        1.0:  "Normal",
        1.25: "1.25", 1.5: "1.5", 1.75: "1.75", 2.0: "2"
    }

    def __init__(self):
        self._driver: Optional[object]               = None
        self._wait:   Optional[object]               = None
        self._sleep_timer: Optional[threading.Timer] = None
        self._current_query: str                     = ""
        self._is_launched: bool                      = False
        self._pre_duck_volume: int                   = 100  # saved before ducking
        self._lock = threading.Lock()

    # ══════════════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _check_selenium(self):
        if not SELENIUM_AVAILABLE:
            raise YTSeleniumMissingError(
                "Selenium or webdriver-manager is not installed.\n"
                "Run: pip install selenium webdriver-manager"
            )

    def _check_launched(self):
        """Ensure the browser is open and responsive."""
        if not self._is_launched or self._driver is None:
            raise YTNotLaunchedError(
                "YouTube is not open. Say 'play <song name>' first."
            )
        try:
            _ = self._driver.current_url
        except (WebDriverException, NoSuchWindowException):
            self._is_launched = False
            self._driver = None
            raise YTBrowserClosedError(
                "The YouTube browser window was closed. "
                "Say 'play <song>' to reopen."
            )

    def _js(self, script: str, *args):
        """Execute JavaScript safely, returns result or None on error."""
        try:
            return self._driver.execute_script(script, *args)
        except JavascriptException as e:
            log.warning(f"JS error: {e}")
            return None
        except (WebDriverException, NoSuchWindowException):
            self._is_launched = False
            raise YTBrowserClosedError("Browser window was closed.")

    def _click(self, css_selector: str, timeout: float = 5.0) -> bool:
        """Safely click a YouTube UI button. Returns True on success."""
        try:
            element = WebDriverWait(self._driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
            )
            self._driver.execute_script("arguments[0].click();", element)
            return True
        except TimeoutException:
            log.warning(f"Button not clickable within {timeout}s: {css_selector}")
            return False
        except (NoSuchElementException, WebDriverException) as e:
            log.warning(f"Click failed for {css_selector}: {e}")
            return False

    def _wait_for_video_ready(self, timeout: float = 20.0) -> bool:
        """Wait until the video element exists and has readyState >= 2."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                vid = self._driver.find_element(By.CSS_SELECTOR, self._SEL["video"])
                ready = self._js(
                    "const v = arguments[0]; return v.readyState >= 2;", vid
                )
                if ready:
                    return True
            except (NoSuchElementException, WebDriverException):
                pass
            time.sleep(0.5)
        return False

    def _build_driver(self) -> "webdriver.Chrome":
        """Create and return a configured Chrome WebDriver."""
        opts = Options()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--disable-notifications")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        opts.add_experimental_option("prefs", {
            "profile.default_content_setting_values.autoplay": 1
        })
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)

    # ══════════════════════════════════════════════════════════════════════════
    #  AUDIO DUCKING  —  called by main.py around SpeechRecognition()
    # ══════════════════════════════════════════════════════════════════════════

    def duck_volume(self, duck_to: int = 8) -> None:
        """
        Lower YouTube video volume so the microphone can hear the user clearly.
        Saves current volume internally so restore_volume() can undo it.

        Called by main.py BEFORE SpeechRecognition() starts.
        Safe to call when YouTube is not open — silently does nothing.

        Args:
            duck_to: Volume level to duck to (0-100). Default is 8%.
        """
        if not self._is_launched or self._driver is None:
            return

        try:
            _ = self._driver.current_url
        except (WebDriverException, NoSuchWindowException):
            self._is_launched = False
            self._driver = None
            return

        try:
            current = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "return v ? Math.round(v.volume * 100) : null;"
            )
            if current is not None:
                self._pre_duck_volume = int(current)
                self._js(
                    "const v = document.querySelector('video.html5-main-video');"
                    "if(v) v.volume = arguments[0] / 100;",
                    max(0, min(100, int(duck_to)))
                )
                log.info(f"🎙️ Ducked YT volume: {current}% → {duck_to}%")
        except Exception as e:
            log.warning(f"duck_volume() failed silently: {e}")

    def restore_volume(self) -> None:
        """
        Restore YouTube volume to what it was before duck_volume() was called.

        Called by main.py AFTER SpeechRecognition() finishes capturing a query.
        Safe to call when YouTube is not open — silently does nothing.
        """
        if not self._is_launched or self._driver is None:
            return

        try:
            _ = self._driver.current_url
        except (WebDriverException, NoSuchWindowException):
            self._is_launched = False
            self._driver = None
            return

        try:
            restore_to = getattr(self, "_pre_duck_volume", 100)
            self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(v) v.volume = arguments[0] / 100;",
                restore_to
            )
            log.info(f"🔊 Restored YT volume to {restore_to}%")
        except Exception as e:
            log.warning(f"restore_volume() failed silently: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    # ── Launch ────────────────────────────────────────────────────────────────

    def launch(self, query: str) -> str:
        """Search YouTube for `query` and auto-play the first result."""
        self._check_selenium()

        query = query.strip()
        if not query:
            return "Please tell me what song or video you want to play."

        try:
            # Reuse existing browser if alive
            if self._is_launched and self._driver:
                try:
                    _ = self._driver.current_url
                except (WebDriverException, NoSuchWindowException):
                    self._driver = None
                    self._is_launched = False

            if self._driver is None:
                log.info("Launching new Chrome window for YouTube.")
                self._driver = self._build_driver()
                self._wait   = WebDriverWait(self._driver, 15)

            self._current_query = query
            search_url = (
                f"https://www.youtube.com/results?"
                f"search_query={query.replace(' ', '+')}"
            )
            self._driver.get(search_url)

            try:
                self._wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self._SEL["first_result"])
                    )
                )
            except TimeoutException:
                return f"YouTube search timed out for '{query}'. Please try again."

            results = self._driver.find_elements(
                By.CSS_SELECTOR, self._SEL["first_result"]
            )
            if not results:
                return f"No results found for '{query}' on YouTube."

            clicked = False
            for result in results[:5]:
                href = result.get_attribute("href") or ""
                if "/watch?v=" in href:
                    self._driver.execute_script("arguments[0].click();", result)
                    clicked = True
                    break
            if not clicked:
                results[0].click()

            self._wait_for_video_ready(timeout=25)
            self._dismiss_dialogs()
            self._is_launched = True
            log.info(f"Now playing: {query}")
            return f"Now playing {query} on YouTube."

        except SessionNotCreatedException:
            self._driver = None
            self._is_launched = False
            return (
                "Could not start Chrome. Make sure Google Chrome is "
                "installed and up to date."
            )
        except WebDriverException as e:
            self._driver = None
            self._is_launched = False
            return f"Browser error while launching YouTube: {str(e)[:80]}"
        except Exception as e:
            return f"Something went wrong while opening YouTube: {str(e)[:80]}"

    def _dismiss_dialogs(self):
        """Silently dismiss common YouTube dialogs (cookies, ads)."""
        for sel in [
            "button[aria-label='Accept all']",
            "button[aria-label='Agree']",
            "button.ytp-ad-skip-button",
        ]:
            try:
                btn = self._driver.find_element(By.CSS_SELECTOR, sel)
                self._driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
            except Exception:
                pass

    # ── Play / Pause ──────────────────────────────────────────────────────────

    def play_pause(self) -> str:
        self._check_launched()
        try:
            state = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(!v) return null;"
                "if(v.paused){ v.play(); return 'playing'; }"
                "else { v.pause(); return 'paused'; }"
            )
            if state is None:
                raise YTNoVideoError("No video element found.")
            return f"Video {state}."
        except (YTBrowserClosedError, YTNoVideoError):
            raise
        except Exception as e:
            return f"Could not toggle playback: {str(e)[:60]}"

    def play(self) -> str:
        self._check_launched()
        try:
            self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(v) v.play();"
            )
            return "Video playing."
        except Exception as e:
            return f"Could not play: {str(e)[:60]}"

    def pause(self) -> str:
        self._check_launched()
        try:
            self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(v) v.pause();"
            )
            return "Video paused."
        except Exception as e:
            return f"Could not pause: {str(e)[:60]}"

    # ── Skip / Seek ───────────────────────────────────────────────────────────

    def skip(self, seconds: float) -> str:
        self._check_launched()
        try:
            if seconds == 0:
                return "Skip amount is zero — nothing changed."
            result = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(!v) return 'no_video';"
                "const t = Math.max(0, Math.min(v.currentTime + arguments[0], v.duration - 1));"
                "v.currentTime = t; return t;",
                float(seconds)
            )
            if result == "no_video":
                raise YTNoVideoError("No video element found.")
            direction = "forward" if seconds > 0 else "backward"
            return f"Skipped {direction} {abs(int(seconds))} seconds."
        except (YTBrowserClosedError, YTNoVideoError):
            raise
        except Exception as e:
            return f"Could not skip: {str(e)[:60]}"

    # ── Volume / Mute ─────────────────────────────────────────────────────────

    def set_volume(self, percent: int) -> str:
        self._check_launched()
        try:
            percent = max(0, min(100, int(percent)))
            self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(v){ v.volume = arguments[0] / 100; v.muted = false; }",
                percent
            )
            self._pre_duck_volume = percent  # keep saved vol in sync
            return f"Volume set to {percent} percent."
        except Exception as e:
            return f"Could not set volume: {str(e)[:60]}"

    def toggle_mute(self) -> str:
        self._check_launched()
        try:
            state = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(!v) return null;"
                "v.muted = !v.muted;"
                "return v.muted ? 'muted' : 'unmuted';"
            )
            if state is None:
                raise YTNoVideoError("No video element found.")
            return f"Video {state}."
        except (YTBrowserClosedError, YTNoVideoError):
            raise
        except Exception as e:
            return f"Could not toggle mute: {str(e)[:60]}"

    # ── Fullscreen ────────────────────────────────────────────────────────────

    def toggle_fullscreen(self) -> str:
        self._check_launched()
        try:
            is_full = self._js("return document.fullscreenElement !== null;")
            if is_full:
                self._js("document.exitFullscreen();")
                return "Exited fullscreen."
            else:
                clicked = self._click(self._SEL["fullscreen_btn"], timeout=4)
                if not clicked:
                    self._js(
                        "const v = document.querySelector('video.html5-main-video');"
                        "if(v) v.requestFullscreen();"
                    )
                return "Fullscreen enabled."
        except Exception as e:
            return f"Could not toggle fullscreen: {str(e)[:60]}"

    # ── Captions ──────────────────────────────────────────────────────────────

    def toggle_captions(self) -> str:
        self._check_launched()
        try:
            clicked = self._click(self._SEL["captions_btn"], timeout=4)
            if clicked:
                state = self._js(
                    "const btn = document.querySelector('.ytp-subtitles-button');"
                    "return btn ? btn.getAttribute('aria-pressed') : null;"
                )
                status = "on" if state == "true" else "off"
                return f"Captions turned {status}."
            return "Captions button not found. This video may not have captions."
        except Exception as e:
            return f"Could not toggle captions: {str(e)[:60]}"

    # ── Theater Mode ──────────────────────────────────────────────────────────

    def toggle_theater(self) -> str:
        self._check_launched()
        try:
            clicked = self._click(self._SEL["theater_btn"], timeout=4)
            return "Theater mode toggled." if clicked else "Theater mode button not found."
        except Exception as e:
            return f"Could not toggle theater mode: {str(e)[:60]}"

    # ── Ambient Mode ──────────────────────────────────────────────────────────

    def toggle_ambient(self) -> str:
        self._check_launched()
        try:
            if not self._click(self._SEL["settings_btn"], timeout=4):
                return "Could not open YouTube settings menu."
            time.sleep(0.6)
            try:
                ambient = WebDriverWait(self._driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//div[contains(@class,'ytp-menuitem')]"
                         "[.//div[contains(text(),'Ambient')]]")
                    )
                )
                self._driver.execute_script("arguments[0].click();", ambient)
                return "Ambient mode toggled."
            except TimeoutException:
                self._click(self._SEL["settings_btn"], timeout=3)
                return "Ambient mode option not found for this video."
        except Exception as e:
            return f"Could not toggle ambient mode: {str(e)[:60]}"

    # ── Autoplay ──────────────────────────────────────────────────────────────

    def toggle_autoplay(self) -> str:
        self._check_launched()
        try:
            state_before = self._js(
                "const btn = document.querySelector('.ytp-autonav-toggle-button');"
                "return btn ? btn.getAttribute('aria-checked') : null;"
            )
            clicked = self._click(self._SEL["autoplay_btn"], timeout=4)
            if clicked:
                new_state = "on" if state_before == "false" else "off"
                return f"Autoplay turned {new_state}."
            return "Autoplay button not found."
        except Exception as e:
            return f"Could not toggle autoplay: {str(e)[:60]}"

    # ── Playback Speed ────────────────────────────────────────────────────────

    def set_speed(self, rate: float) -> str:
        self._check_launched()
        valid_rates = sorted(self._SPEED_LABELS.keys())
        rate = float(rate)
        if rate <= 0:
            return "Speed must be greater than zero."
        closest = min(valid_rates, key=lambda x: abs(x - rate))
        try:
            result = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(!v) return 'no_video';"
                "v.playbackRate = arguments[0];"
                "return v.playbackRate;",
                closest
            )
            if result == "no_video":
                raise YTNoVideoError("No video element found.")
            label = "Normal speed" if closest == 1.0 else f"{self._SPEED_LABELS[closest]}x speed"
            return f"Playback speed set to {label}."
        except (YTBrowserClosedError, YTNoVideoError):
            raise
        except Exception as e:
            return f"Could not set speed: {str(e)[:60]}"

    # ── Sleep Timer ───────────────────────────────────────────────────────────

    def set_sleep_timer(self, minutes: float) -> str:
        self._check_launched()
        with self._lock:
            if minutes <= 0:
                return "Sleep timer must be more than 0 minutes."
            if self._sleep_timer and self._sleep_timer.is_alive():
                self._sleep_timer.cancel()

            def _action():
                try:
                    self.pause()
                    log.info("Sleep timer fired — video paused.")
                except Exception as e:
                    log.warning(f"Sleep timer action failed: {e}")

            self._sleep_timer = threading.Timer(minutes * 60, _action)
            self._sleep_timer.daemon = True
            self._sleep_timer.start()

            m = int(minutes)
            s = int((minutes - m) * 60)
            time_str = f"{m} minute{'s' if m != 1 else ''}"
            if s:
                time_str += f" {s} second{'s' if s != 1 else ''}"
            return f"Sleep timer set. Video will pause in {time_str}."

    def cancel_sleep_timer(self) -> str:
        with self._lock:
            if self._sleep_timer and self._sleep_timer.is_alive():
                self._sleep_timer.cancel()
                self._sleep_timer = None
                return "Sleep timer cancelled."
            return "No active sleep timer to cancel."

    def get_sleep_timer_status(self) -> str:
        with self._lock:
            if self._sleep_timer and self._sleep_timer.is_alive():
                return "Sleep timer is active."
            return "No sleep timer is set."

    # ── Navigation ────────────────────────────────────────────────────────────

    def next_video(self) -> str:
        self._check_launched()
        try:
            clicked = self._click(self._SEL["next_btn"], timeout=4)
            return "Playing next video." if clicked else "Next button not found."
        except Exception as e:
            return f"Could not go to next video: {str(e)[:60]}"

    def prev_video(self) -> str:
        self._check_launched()
        try:
            current_time = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "return v ? v.currentTime : null;"
            )
            if current_time is None:
                raise YTNoVideoError("No video element found.")
            if current_time > 5:
                self._js(
                    "document.querySelector('video.html5-main-video').currentTime = 0;"
                )
                return "Restarted the current video."
            else:
                self._driver.back()
                time.sleep(1.5)
                return "Going to previous page."
        except (YTBrowserClosedError, YTNoVideoError):
            raise
        except Exception as e:
            return f"Could not go to previous: {str(e)[:60]}"

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> str:
        self._check_launched()
        try:
            info = self._js(
                "const v = document.querySelector('video.html5-main-video');"
                "if(!v) return null;"
                "return {"
                "  paused: v.paused,"
                "  currentTime: v.currentTime,"
                "  duration: v.duration,"
                "  volume: Math.round(v.volume * 100),"
                "  muted: v.muted,"
                "  speed: v.playbackRate"
                "};"
            )
            if not info:
                raise YTNoVideoError("No video element found.")
            state   = "Paused" if info["paused"] else "Playing"
            cur     = int(info["currentTime"])
            dur     = int(info["duration"]) if info["duration"] else 0
            cur_fmt = f"{cur // 60}:{cur % 60:02d}"
            dur_fmt = f"{dur // 60}:{dur % 60:02d}" if dur else "unknown"
            return (
                f"Status: {state}. "
                f"Time: {cur_fmt} of {dur_fmt}. "
                f"Volume: {info['volume']}%{' (muted)' if info['muted'] else ''}. "
                f"Speed: {info['speed']}x. "
                f"{self.get_sleep_timer_status()}"
            )
        except (YTBrowserClosedError, YTNoVideoError):
            raise
        except Exception as e:
            return f"Could not read status: {str(e)[:60]}"

    # ── Close ─────────────────────────────────────────────────────────────────

    def close(self) -> str:
        self.cancel_sleep_timer()
        if self._driver:
            try:
                self._driver.quit()
            except Exception as e:
                log.warning(f"Error closing browser: {e}")
            finally:
                self._driver      = None
                self._wait        = None
                self._is_launched = False
        return "YouTube closed."

    # ══════════════════════════════════════════════════════════════════════════
    #  VOICE COMMAND PARSER
    # ══════════════════════════════════════════════════════════════════════════

    def parse_and_execute(self, command: str) -> str:
        """
        Parse a voice command and execute the matching action.
        Command is the text AFTER the 'youtube control' prefix is stripped.
        """
        cmd = command.lower().strip()
        is_play_cmd = cmd.startswith("play ") or cmd == "play"

        if not is_play_cmd and not self._is_launched:
            return (
                "YouTube is not open yet. "
                "Say 'play' followed by a song name to start."
            )

        try:
            if is_play_cmd:
                return self.launch(cmd.removeprefix("play").strip())

            if any(w in cmd for w in ["pause", "stop video"]):
                return self.pause()

            if any(w in cmd for w in ["resume", "continue", "unpause", "start video"]):
                return self.play()

            if cmd in ("toggle", "play pause", "toggle play"):
                return self.play_pause()

            if any(w in cmd for w in ["fullscreen", "full screen", "exit full"]):
                return self.toggle_fullscreen()

            if any(w in cmd for w in ["caption", "subtitle", "cc"]):
                return self.toggle_captions()

            if any(w in cmd for w in ["theater", "theatre", "cinema mode"]):
                return self.toggle_theater()

            if "ambient" in cmd:
                return self.toggle_ambient()

            if any(w in cmd for w in ["autoplay", "auto play", "auto-play"]):
                return self.toggle_autoplay()

            if any(w in cmd for w in ["mute", "unmute", "silence"]):
                return self.toggle_mute()

            if "volume" in cmd:
                match = re.search(r"(\d+)", cmd)
                if match:
                    return self.set_volume(int(match.group(1)))
                cur = self._js(
                    "const v=document.querySelector('video.html5-main-video');"
                    "return v?Math.round(v.volume*100):50;"
                ) or 50
                if any(w in cmd for w in ["up", "louder", "increase"]):
                    return self.set_volume(min(100, cur + 10))
                if any(w in cmd for w in ["down", "quieter", "decrease", "lower"]):
                    return self.set_volume(max(0, cur - 10))
                return "Please say a volume level, like 'volume 70'."

            if any(w in cmd for w in ["speed", "playback rate", "faster", "slower",
                                       "slow down", "speed up", "normal speed"]):
                if "normal" in cmd:
                    return self.set_speed(1.0)
                cur_speed = self._js(
                    "const v=document.querySelector('video.html5-main-video');"
                    "return v?v.playbackRate:1;"
                ) or 1.0
                if any(w in cmd for w in ["slow down", "slower"]):
                    return self.set_speed(max(0.25, cur_speed - 0.25))
                if any(w in cmd for w in ["speed up", "faster"]):
                    return self.set_speed(min(2.0, cur_speed + 0.25))
                match = re.search(r"(\d+\.?\d*)", cmd)
                if match:
                    return self.set_speed(float(match.group(1)))
                return "Please say a speed like 'speed 1.5' or 'slow down'."

            if any(w in cmd for w in ["skip forward", "forward", "fast forward"]):
                match = re.search(r"(\d+)", cmd)
                return self.skip(int(match.group(1)) if match else 10)

            if any(w in cmd for w in ["skip back", "backward", "rewind", "go back"]):
                match = re.search(r"(\d+)", cmd)
                return self.skip(-(int(match.group(1)) if match else 10))

            if any(w in cmd for w in ["next video", "next song", "skip video", "next track"]):
                return self.next_video()

            if any(w in cmd for w in ["previous", "prev", "restart", "replay",
                                       "start over", "beginning"]):
                return self.prev_video()

            if any(w in cmd for w in ["sleep timer", "stop after", "pause after"]):
                match = re.search(r"(\d+\.?\d*)", cmd)
                if match:
                    return self.set_sleep_timer(float(match.group(1)))
                return "Please say how many minutes, like 'sleep timer 30'."

            if any(w in cmd for w in ["cancel timer", "stop timer", "remove timer",
                                       "clear timer", "no timer"]):
                return self.cancel_sleep_timer()

            if any(w in cmd for w in ["status", "what's playing",
                                       "current video", "what is playing"]):
                return self.get_status()

            if any(w in cmd for w in ["close youtube", "quit youtube", "exit youtube",
                                       "close video", "close browser"]):
                return self.close()

            log.warning(f"Unrecognized command: '{cmd}'")
            return (
                f"I didn't understand '{command}'. "
                "Try: pause, fullscreen, captions, speed 1.5, "
                "sleep timer 30, volume 70, or close YouTube."
            )

        except YTNotLaunchedError as e:
            return str(e)
        except YTBrowserClosedError as e:
            return str(e)
        except YTNoVideoError as e:
            return str(e)
        except YTSeleniumMissingError as e:
            return str(e)
        except YTControllerError as e:
            return f"YouTube controller error: {str(e)}"
        except Exception as e:
            log.error(f"Unexpected error in parse_and_execute: {e}")
            return f"Unexpected error: {str(e)[:80]}"

    def __del__(self):
        try:
            if self._driver:
                self._driver.quit()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────
yt_controller = YouTubePlayer()


# ─────────────────────────────────────────────────────────────────────────────
#  Quick interactive test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🎬 YouTubeController — Interactive Test")
    print("Commands: play <song>, pause, resume, fullscreen, captions,")
    print("          theater, ambient, autoplay, speed 1.5, skip forward 10,")
    print("          volume 80, sleep timer 5, cancel timer, status, close\n")

    controller = YouTubePlayer()
    while True:
        try:
            user_input = input("Command: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                controller.close()
                break
            print(f"→ {controller.parse_and_execute(user_input)}\n")
        except KeyboardInterrupt:
            controller.close()
            break