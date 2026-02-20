import threading
import time
import json
from typing import Any, Dict

from .memory import Memory
from .guard import build_prompt, judge, enforce, Judgment
from .llm import generate_response
from .intent_judge import IntentJudge
from skill_manager import SkillManager


class CrystalBrain:
    """
    CrystalBrain v7.0 — Autonomous Agent Core

    Architecture:
    - Manual Skill Lock Mode
    - Semantic Intent Routing
    - Autonomous Multi-Step Agent Loop
    - Deterministic Skill Execution
    - Safe LLM Fallback
    """

    def __init__(
        self,
        skill_manager: SkillManager,
        awareness: dict = None,
        temp_conversation: float = 0.2,
        temp_skill: float = 0.1,
    ):
        self.memory = Memory()
        self.skill_manager = skill_manager
        self.awareness = awareness or {}
        self.temp_conversation = temp_conversation
        self.temp_skill = temp_skill

        # Skill Lock Mode
        self.active_skill = None

        # Autonomous Agent Settings
        self.agent_mode = True
        self.max_agent_steps = 5

        # Intent Engine
        self.judge = IntentJudge(self.skill_manager)

        # Map intents → skill instances
        self.intent_skill_map = self._build_intent_skill_map()

        # Background monitor
        self.monitor_active = True
        self.monitor_thread = threading.Thread(
            target=self._background_monitor,
            daemon=True
        )
        self.monitor_thread.start()

        print(f"🌌 Crystal Brain v7 Online. {len(self.intent_skill_map)} intents mapped.")

    # ==================================================
    # MAIN PROCESS PIPELINE
    # ==================================================

    def process(self, user_text: str) -> str:
        self._trace("RECV", "GUI", user_text)

        user_text = user_text.strip()
        lowered = user_text.lower()

        # ------------------------------------------------
        # 1️⃣ SKILL LOCK COMMANDS
        # ------------------------------------------------

        if lowered.startswith("use ") and "skill" in lowered:
            skill_name = lowered.replace("use", "").replace("skill", "").strip()
            if skill_name in self.intent_skill_map:
                self.active_skill = skill_name
                return f"🔒 {skill_name.replace('_', ' ').title()} mode activated."
            return "Skill not found."

        if lowered in ["exit", "leave skill", "stop mode"]:
            self.active_skill = None
            return "🔓 Returned to global mode."

        # ------------------------------------------------
        # 2️⃣ LOCKED MODE EXECUTION
        # ------------------------------------------------

        if self.active_skill:
            skill = self.intent_skill_map.get(self.active_skill)
            if skill:
                result = skill.run({
                    "user_input": user_text,
                    "intent": self.active_skill,
                    "mode": "locked"
                })
                return result

        # ------------------------------------------------
        # 3️⃣ SEMANTIC INTENT DETECTION
        # ------------------------------------------------

        intent_result = self.judge.detect_intent(user_text)

        action = intent_result.get("action")
        intent_name = intent_result.get("intent", "").lower()
        confidence = intent_result.get("confidence", 1.0)

        # ------------------------------------------------
        # 4️⃣ AUTONOMOUS AGENT TRIGGER
        # ------------------------------------------------

        if self.agent_mode:
            complex_markers = [" and ", " then ", "after that", "also"]

            if any(marker in lowered for marker in complex_markers):
                return self._run_agent(user_text)

        # ------------------------------------------------
        # 5️⃣ LOW CONFIDENCE SUGGESTION
        # ------------------------------------------------

        if confidence < 0.65 and intent_result.get("candidates"):
            options = ", ".join(intent_result["candidates"])
            return f"I am not fully certain. Did you mean: {options}?"

        # ------------------------------------------------
        # 6️⃣ SINGLE SKILL EXECUTION
        # ------------------------------------------------

        if action == "execute" and intent_name:
            skill_instance = self.intent_skill_map.get(intent_name)

            if skill_instance:
                skill_output = skill_instance.run({
                    "user_input": user_text,
                    "intent": intent_name,
                    "mode": "semantic"
                })

                if isinstance(skill_output, str) and len(skill_output) < 500:
                    return skill_output

                return self._synthesize(user_text, skill_output)

        # ------------------------------------------------
        # 7️⃣ CONFIRM / CLARIFY
        # ------------------------------------------------

        if action == "confirm":
            return f"I think you want me to {intent_name.replace('_', ' ')}. Shall I proceed?"

        if action == "clarify":
            options = ", ".join(intent_result.get("candidates", []))
            return f"Did you mean: {options}?"

        # ------------------------------------------------
        # 8️⃣ LLM FALLBACK
        # ------------------------------------------------

        return self._llm_fallback(user_text)

    # ==================================================
    # AUTONOMOUS AGENT LOOP
    # ==================================================

    def _run_agent(self, goal: str) -> str:
        plan = self._agent_plan(goal)

        if not plan or "steps" not in plan:
            return "I could not construct a structured task plan."

        results = []
        steps = plan["steps"][:self.max_agent_steps]

        for i, step in enumerate(steps):
            skill_name = step.get("skill", "").lower()
            step_input = step.get("input", "")

            skill = self.intent_skill_map.get(skill_name)

            if not skill:
                results.append(f"[Step {i+1}] Unknown skill: {skill_name}")
                continue

            self._trace("SEND", "AGENT", f"{i+1}: {skill_name}")

            output = skill.run({
                "user_input": step_input,
                "intent": skill_name,
                "mode": "agent"
            })

            results.append(f"[Step {i+1}] {output}")

        return "\n".join(results)

    def _agent_plan(self, goal: str) -> dict:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a task planner. "
                    "Break the user request into executable skill steps. "
                    "Return strict JSON format:\n"
                    "{ \"steps\": [ {\"skill\": \"intent_name\", \"input\": \"text\"} ] }"
                )
            },
            {"role": "user", "content": goal}
        ]

        raw = generate_response(messages=messages, temperature=0.1)

        try:
            return json.loads(raw)
        except:
            return {}

    # ==================================================
    # SYNTHESIS
    # ==================================================

    def _synthesize(self, user_text: str, skill_output: str) -> str:
        recall = self.memory.query_entities(user_text) or "No prior context."
        gate = build_prompt(user_text)

        final_messages = [
            {"role": "system", "content": gate["system_prompt"]},
            *self.memory.context(last_n=6),
            {
                "role": "user",
                "content": (
                    f"CONTEXT: {recall}\n"
                    f"SKILL DATA: {skill_output}\n"
                    f"USER: {user_text}\n\n"
                    "Respond naturally using SKILL DATA as truth."
                )
            }
        ]

        final = generate_response(
            messages=final_messages,
            temperature=self.temp_conversation,
        )

        if judge(final, gate["rules"]) == Judgment.FAIL:
            final = enforce(final, gate["rules"])

        self.memory.add("assistant", final)
        return final

    # ==================================================
    # LLM FALLBACK
    # ==================================================

    def _llm_fallback(self, user_text: str) -> str:
        gate = build_prompt(user_text)

        messages = [
            {"role": "system", "content": gate["system_prompt"]},
            *self.memory.context(last_n=6),
            {"role": "user", "content": user_text}
        ]

        response = generate_response(
            messages=messages,
            temperature=self.temp_conversation,
        )

        if judge(response, gate["rules"]) == Judgment.FAIL:
            response = enforce(response, gate["rules"])

        self.memory.add("assistant", response)
        return response

    # ==================================================
    # UTILITIES
    # ==================================================

    def _build_intent_skill_map(self) -> Dict[str, Any]:
        mapping = {}
        for skill_info in self.skill_manager.skills:
            instance = skill_info.get("instance")
            if instance:
                intents = getattr(instance, "supported_intents", [])
                for intent in intents:
                    mapping[intent.lower()] = instance
        return mapping

    def _trace(self, direction: str, branch: str, payload: Any):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [BRAIN:{branch}] {direction} -> {payload}")

    def _background_monitor(self):
        while self.monitor_active:
            try:
                for skill_info in self.skill_manager.skills:
                    instance = skill_info.get("instance")
                    if instance:
                        for hook in ["check_queue_loop", "weather_monitor"]:
                            fn = getattr(instance, hook, None)
                            if callable(fn):
                                fn()
                time.sleep(10)
            except:
                time.sleep(10)
    def stream_process(self, user_text):
        response = self.process(user_text)

        # Fake token streaming (works even if LLM is not streaming)
        for word in response.split():
            yield word + " "
            time.sleep(0.03)
