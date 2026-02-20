import json
import os
from flashtext import KeywordProcessor
from sentence_transformers import SentenceTransformer, util
import torch


class IntentJudge:
    def __init__(self, skill_manager=None, config_path="core/custom_commands.json"):
        self.MODEL_NAME = "all-MiniLM-L6-v2"
        self.HIGH_CONFIDENCE = 0.65
        self.MEDIUM_CONFIDENCE = 0.45
        self.AMBIGUITY_MARGIN = 0.07
        self.config_path = config_path

        print(f"🧠 [JUDGE]: Initializing Semantic Engine ({self.MODEL_NAME})...")
        self.model = SentenceTransformer(self.MODEL_NAME)

        # Load intents
        self.intents, self.imperative_verbs = self._load_data()

        print(f"⚡ [JUDGE]: Precomputing embeddings for {len(self.intents)} intents...")
        self.intent_embeddings = {
            intent: self.model.encode(phrases, convert_to_tensor=True)
            for intent, phrases in self.intents.items()
        }

        # Keyword gate
        self.keyword_processor = KeywordProcessor(case_sensitive=False)
        self._setup_keyword_gate()

    # =========================================================
    # DATA LOADING
    # =========================================================

    def _load_data(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                data = json.load(f)
                verbs = data.pop("imperative_verbs", [])
                return data, verbs

        print("⚠️ [JUDGE]: custom_commands.json not found. Using defaults.")

        default_intents = {
            "app_pilot": ["open application", "launch app", "open website", "open youtube"],
            "music_skill": ["play music", "play song", "pause music", "skip track"],
            "camera_skill": ["open camera", "take picture", "take photo"],
            "weather_sentinel": ["weather forecast", "current weather", "temperature outside"],
            "clock": ["what time is it", "current time"],
            "file_commander": ["move file", "copy file", "delete file", "list files"],
            "email_skill": ["check email", "open inbox", "send email"],
            "web_researcher": ["research topic", "summarize article", "find information"],
            "reminder_skill": ["set reminder", "remind me"],
            "smart_home": ["turn on light", "turn off device"],
            "system_sentinel": ["system status", "battery level", "cpu usage"],
            "wifi_scanner": ["scan wifi", "network scan"],
            "osint_investigator": ["find person", "background check"],
            "location_sentinel": ["where am i", "current location"],
            "greet": ["hello", "hi crystal", "wake up"]
        }

        default_verbs = [
            "open", "launch", "start", "play",
            "search", "watch", "move", "delete",
            "scan", "set", "check"
        ]

        return default_intents, default_verbs

    # =========================================================
    # KEYWORD GATE
    # =========================================================

    def _setup_keyword_gate(self):
        for phrases in self.intents.values():
            for phrase in phrases:
                if len(phrase.split()) <= 2:
                    self.keyword_processor.add_keyword(phrase)

        for verb in self.imperative_verbs:
            self.keyword_processor.add_keyword(verb)

    # =========================================================
    # INTENT DETECTION
    # =========================================================

    def detect_intent(self, text: str):
        text = text.lower().strip()

        if not text:
            return {"action": "none"}

        print(f"\n🧠 [JUDGE]: Analyzing → {text}")

        # 1️⃣ KEYWORD CHECK (Speed Boost, Not Hard Block)
        keywords = self.keyword_processor.extract_keywords(text)
        first_word = text.split()[0] if text.split() else ""

        print(f"🧠 [JUDGE]: Keywords → {keywords}")

        # 2️⃣ SEMANTIC EVALUATION
        text_emb = self.model.encode(text, convert_to_tensor=True)

        scores = []
        for intent, emb in self.intent_embeddings.items():
            score = util.cos_sim(text_emb, emb).max().item()
            scores.append((intent, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        top_intent, top_score = scores[0]
        print(f"🧠 [JUDGE]: Top Intent → {top_intent} ({top_score:.3f})")

        # 3️⃣ Ambiguity Detection
        close_matches = [
            intent for intent, score in scores[1:]
            if abs(top_score - score) <= self.AMBIGUITY_MARGIN
        ]

        if close_matches and top_score >= self.MEDIUM_CONFIDENCE:
            print("🧠 [JUDGE]: Ambiguous match detected.")
            return {
                "action": "clarify",
                "intent": top_intent,
                "confidence": round(top_score, 3),
                "candidates": [top_intent] + close_matches
            }

        # 4️⃣ Final Routing
        if top_score >= self.HIGH_CONFIDENCE:
            print("🧠 [JUDGE]: High confidence execution.")
            return {
                "action": "execute",
                "intent": top_intent,
                "confidence": round(top_score, 3)
            }

        if top_score >= self.MEDIUM_CONFIDENCE:
            print("🧠 [JUDGE]: Medium confidence — confirmation required.")
            return {
                "action": "confirm",
                "intent": top_intent,
                "confidence": round(top_score, 3)
            }

        print("🧠 [JUDGE]: No suitable intent.")
        return {"action": "none"}
