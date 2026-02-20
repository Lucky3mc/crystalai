import subprocess
import pyautogui
import time
import os
import webbrowser
import glob
from typing import Optional, Tuple
from skill_manager import Skill

# -------------------- Selenium Setup --------------------

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    print("⚠️ Selenium not installed. Streaming automation limited.")
    SELENIUM_AVAILABLE = False


# =========================================================
#                     APP PILOT SKILL
# =========================================================

class AppPilotSkill(Skill):
    name = "AppPilot"
    description = "Opens apps, streams content, and automates desktop actions"
    keywords = ["open", "watch", "stream", "search", "type", "calculate", "go to"]
    supported_intents = ["app_pilot"]


    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):
        self.driver = None

        # Streaming sites
        self.streaming_sites = {
            "9anime": "https://9animetv.to",
            "hdtoday": "https://hdtoday.tv",
            "netflix": "https://www.netflix.com",
            "primevideo": "https://www.primevideo.com",
            "disneyplus": "https://www.disneyplus.com",
            "crunchyroll": "https://www.crunchyroll.com",
            "hulu": "https://www.hulu.com"
        }

        # App paths
        self.app_paths = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": self._get_chrome_path(),
            "vscode": self._get_vscode_path(),
            "spotify": self._get_spotify_path(),
            "discord": self._get_discord_path(),
        }

        # Aliases
        self.aliases = {
            "browser": "chrome",
            "google": "chrome",
            "code": "vscode",
            "music": "spotify",
            "movie": "hdtoday",
            "anime": "9anime",
            "amazon": "primevideo",
            "disney": "disneyplus"
        }

        print("✅ [APP PILOT]: Production version loaded")

    # =====================================================
    # PATH HELPERS
    # =====================================================

    def _get_chrome_path(self):
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return "chrome"

    def _get_vscode_path(self):
        username = os.getlogin()
        paths = [
            rf"C:\Users\{username}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            r"C:\Program Files\Microsoft VS Code\Code.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return "code"

    def _get_spotify_path(self):
        username = os.getlogin()
        paths = [
            rf"C:\Users\{username}\AppData\Roaming\Spotify\Spotify.exe",
            rf"C:\Users\{username}\AppData\Local\Microsoft\WindowsApps\Spotify.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return "spotify"

    def _get_discord_path(self):
        username = os.getlogin()
        paths = glob.glob(
            rf"C:\Users\{username}\AppData\Local\Discord\app-*\Discord.exe"
        )
        if paths:
            return paths[0]
        return "discord"

    # =====================================================
    # SELENIUM INIT
    # =====================================================

    def _init_selenium(self):
        if not SELENIUM_AVAILABLE:
            return False
        if self.driver:
            return True

        try:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--autoplay-policy=no-user-gesture-required")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            print("⚠️ Selenium init failed:", e)
            return False

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize(self, target: str) -> str:
        target = target.lower().strip()
        if target in self.aliases:
            return self.aliases[target]
        return target

    # =====================================================
    # CORE ACTIONS
    # =====================================================

    def _open_app(self, name: str):
        name = self._normalize(name)

        # Streaming site
        if name in self.streaming_sites:
            return self._open_url(self.streaming_sites[name])

        # Installed app
        if name in self.app_paths:
            try:
                subprocess.Popen(self.app_paths[name])
                return f"Opened {name}"
            except Exception as e:
                return f"Failed to open {name}: {e}"

        # URL fallback
        if "." in name:
            return self._open_url("https://" + name)

        return f"Unknown application: {name}"

    def _open_url(self, url: str):
        if self._init_selenium():
            self.driver.get(url)
            return f"Opened {url} in Chrome"
        else:
            webbrowser.open(url)
            return f"Opened {url} in browser"

    def _type_text(self, text: str):
        time.sleep(1)
        pyautogui.write(text, interval=0.05)
        return f"Typed: {text}"

    def _calculate(self, expr: str):
        subprocess.Popen("calc.exe")
        time.sleep(2)
        pyautogui.write(expr)
        pyautogui.press("enter")
        return f"Calculated: {expr}"

    def _search_google(self, query: str):
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self._open_url(url)

    def _stream_content(self, site: str, content: str):
        site = self._normalize(site)

        if site not in self.streaming_sites:
            return f"Streaming site {site} not supported"

        search_url = self.streaming_sites[site] + f"/search?q={content.replace(' ', '+')}"
        return self._open_url(search_url)

    # =====================================================
    # INTENT FALLBACK
    # =====================================================

    def _map_input_to_intent(self, text: str):
        text = text.lower().strip()

        if text.startswith(("open ", "launch ", "start ")):
            return "open_application"
        if text.startswith(("go to ", "visit ")):
            return "navigate"
        if text.startswith(("watch ", "stream ", "movie ", "anime ")):
            return "stream_content"
        if text.startswith(("type ", "write ")):
            return "type_text"
        if text.startswith(("search ", "look up ")):
            return "search_content"
        if text.startswith(("calculate ", "compute ")):
            return "calculate_expression"

        return None

    # =====================================================
    # RUN
    # =====================================================

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").strip()

        if not user_input:
            return "No command received."

        intent = self._map_input_to_intent(user_input)

        if intent == "open_application":
            target = user_input.split(" ", 1)[1]
            return self._open_app(target)

        if intent == "navigate":
            target = user_input.replace("go to", "").replace("visit", "").strip()
            return self._open_url("https://" + target)

        if intent == "stream_content":
            words = user_input.split(" on ")
            if len(words) == 2:
                content = words[0].replace("watch", "").replace("stream", "").strip()
                site = words[1].strip()
                return self._stream_content(site, content)
            return "Specify site: e.g., watch Naruto on 9anime"

        if intent == "type_text":
            text = user_input.replace("type", "").replace("write", "").strip()
            return self._type_text(text)

        if intent == "search_content":
            query = user_input.replace("search", "").replace("look up", "").strip()
            return self._search_google(query)

        if intent == "calculate_expression":
            expr = user_input.replace("calculate", "").replace("compute", "").strip()
            return self._calculate(expr)

        return "Command not recognized."

    # =====================================================
    # CLEANUP
    # =====================================================

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Selenium closed")
            except:
                pass
    def run(self, parameters):
        if isinstance(parameters, str):
           user_input = parameters.strip()
        else:
           user_input = parameters.get("user_input", "").strip()

