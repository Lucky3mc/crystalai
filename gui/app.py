import sys
import os
import json
import time
import threading
import pyaudio
import streamlit as st
from vosk import Model, KaldiRecognizer

# =====================
# SYSTEM PATH SETUP
# =====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    
from brain.brain import CrystalBrain
from skill_manager import SkillManager
from tts_bridge import speak, stop_speaking  # ✅ Use only this for TTS

# =====================
# CONFIG & ASSETS
# =====================
VOSK_PATH = os.getenv("VOSK_PATH", os.path.join(PROJECT_ROOT, "models", "vosk"))
MEMORY_FILE = os.path.join(PROJECT_ROOT, "crystal_memory.json")

IMG_IDLE = os.path.join(SCRIPT_DIR, "idle.jpg")
IMG_THINKING = os.path.join(SCRIPT_DIR, "thinking.jpg")
IMG_SPEAKING = os.path.join(SCRIPT_DIR, "speaking.jpg")
IMG_ERROR = os.path.join(SCRIPT_DIR, "error.jpg")
IMG_EXCITED = os.path.join(SCRIPT_DIR, "excited.jpg")

AUDIO_CONFIG = {"format": pyaudio.paInt16, "channels": 1, "rate": 16000, "chunk_size": 4096}
MAX_MEMORY = 100
INTERRUPT_WORDS = ["stop", "cancel", "be quiet", "enough"]

# =====================
# GLOBALS
# =====================
_lock = threading.Lock()

# =====================
# CORE INITIALIZATION
# =====================
@st.cache_resource
def load_crystal_core():
    manager = SkillManager()
    brain = CrystalBrain(manager)
    try:
        vosk_model = Model(VOSK_PATH) if os.path.exists(VOSK_PATH) else None
    except Exception as e:
        st.error(f"Vosk Init Error: {e}")
        vosk_model = None
    return brain, manager, vosk_model

brain, skill_manager, vosk_model = load_crystal_core()

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(page_title="Crystal AI", page_icon="💎", layout="wide")

# =====================
# SESSION STATE
# =====================
if "messages" not in st.session_state:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)
    else:
        st.session_state.messages = []

if "emotion" not in st.session_state: st.session_state.emotion = "idle"
if "active_skill" not in st.session_state: st.session_state.active_skill = None
brain.active_skill = st.session_state.active_skill

# =====================
# VOICE INPUT
# =====================
def listen_voice():
    if not vosk_model:
        st.toast("Voice model not loaded.")
        return ""
    with st.spinner("Listening..."):
        p = pyaudio.PyAudio()
        try:
            rec = KaldiRecognizer(vosk_model, AUDIO_CONFIG["rate"])
            stream = p.open(format=AUDIO_CONFIG["format"], channels=AUDIO_CONFIG["channels"],
                            rate=AUDIO_CONFIG["rate"], input=True,
                            frames_per_buffer=AUDIO_CONFIG["chunk_size"])
            stream.start_stream()
            start = time.time()
            while time.time() - start < 5:
                data = stream.read(AUDIO_CONFIG["chunk_size"], exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    return result.get("text", "")
            final_result = json.loads(rec.FinalResult())
            return final_result.get("text", "")
        except Exception as e:
            st.error(f"Audio Error: {e}")
            return ""
        finally:
            if "stream" in locals():
                stream.stop_stream(); stream.close()
            p.terminate()

# =====================
# INTERACTION HANDLER
# =====================
def handle_interaction(user_text):
    if not user_text.strip(): return
    if user_text.lower().strip() in INTERRUPT_WORDS:
        stop_speaking()
        return

    stop_speaking()
    st.session_state.emotion = "thinking"
    st.session_state.messages.append({"role": "user", "content": user_text})

    placeholder = st.empty()
    full_response = ""
    try:
        for token in brain.stream_process(user_text):
            full_response += token
            placeholder.markdown(full_response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "spoken": False
        })

        # Emotion detection for UI only
        if "error" in full_response.lower(): st.session_state.emotion = "error"
        elif "!" in full_response: st.session_state.emotion = "excited"
        elif "*whisper*" in full_response: st.session_state.emotion = "whisper"
        elif "*laugh*" in full_response: st.session_state.emotion = "happy"
        else: st.session_state.emotion = "speaking"

    except Exception as e:
        error_msg = f"⚠️ Brain Error: {e}"
        st.session_state.messages.append({"role": "assistant", "content": error_msg, "spoken": False})
        st.session_state.emotion = "error"

    # Cap memory
    st.session_state.messages = st.session_state.messages[-MAX_MEMORY:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, indent=2)

    st.rerun()

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.header("💎 Crystal Core")
    status_box = st.container(border=True)
    emo = st.session_state.emotion
    if emo == "thinking": status_box.subheader("🧠 Thinking..."); status_box.image(IMG_THINKING, width=True)
    elif emo == "speaking": status_box.subheader("🗣 Speaking..."); status_box.image(IMG_SPEAKING, width=True)
    elif emo == "error": status_box.subheader("⚠ Error"); status_box.image(IMG_ERROR, width=True)
    elif emo == "excited": status_box.subheader("✨ Excited"); status_box.image(IMG_EXCITED, width=True)
    else: status_box.subheader("🟢 Online"); status_box.image(IMG_IDLE, width=True)

    st.divider()
    if st.session_state.active_skill:
        st.success(f"Mode: {st.session_state.active_skill}")
        if st.button("Exit Skill Mode", use_container_width=True):
            st.session_state.active_skill = None; brain.active_skill = None; st.rerun()
    else: st.info("Mode: Global")

    with st.expander("Skills"):
        for skill_info in skill_manager.skills:
            instance = skill_info.get("instance")
            if not instance: continue
            name = getattr(instance, "name", "Skill")
            intents = getattr(instance, "supported_intents", [])
            if intents and st.button(name, key=f"btn_{name}", use_container_width=True):
                st.session_state.active_skill = intents[0]; brain.active_skill = intents[0]; st.rerun()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        if os.path.exists(MEMORY_FILE): os.remove(MEMORY_FILE)
        st.rerun()

# =====================
# CHAT DISPLAY & AUTO SPEAK
# =====================
def detect_emotion(text: str):
    if "*laugh*" in text: return "happy"
    elif "*whisper*" in text: return "whisper"
    elif "*shout*" in text: return "angry"
    return None

def clean_text(text: str):
    return text.replace("*laugh*", "").replace("*whisper*", "").replace("*shout*", "")

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant":
            emotion = detect_emotion(msg["content"])
            text_to_speak = clean_text(msg["content"])
            
            if st.button("🔊", key=f"replay_{i}") and not _lock.locked():
                stop_speaking()
                speak(text_to_speak, emotion=emotion)

            if not msg.get("spoken", False):
                stop_speaking()
                speak(text_to_speak, emotion=emotion)
                msg["spoken"] = True
                st.session_state.emotion = "idle"

# =====================
# INPUT
# =====================
prompt = st.chat_input("Command Crystal...")
if prompt: handle_interaction(prompt)

st.markdown("---")
c1, c2, c3 = st.columns([1,2,1])
with c2:
    if st.button("🎤 Start Listening", use_container_width=True):
        voice_text = listen_voice()
        if voice_text: handle_interaction(voice_text)
