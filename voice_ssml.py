# voice_ssml.py
import re

# Personality-based voice profiles
VOICE_PROFILES = {
    "gentle":   ("medium", "+2%", "300ms"),
    "playful":  ("fast", "+8%", "150ms"),
    "cold":     ("slow", "-6%", "400ms"),
    "protective": ("medium", "-2%", "250ms"),
}

# Emotion pitch/rate boosts
EMOTION_MODIFIERS = {
    "happy":   ("+10%", "+5%"),
    "sad":     ("-10%", "-5%"),
    "angry":   ("+15%", "+10%"),
    "whisper": ("-20%", "-10%"),
    "excited": ("+12%", "+8%"),
}

def humanize(text: str) -> str:
    """
    Insert natural breaks based on punctuation.
    """
    text = text.replace("...", "<break time='500ms'/>")
    text = text.replace(",", ",<break time='120ms'/>")
    text = text.replace(".", ".<break time='220ms'/>")
    text = text.replace("\n", "<break time='400ms'/>")
    return text

def emphasize_caps(text: str) -> str:
    """
    Add emphasis to words in all caps.
    """
    def repl(match):
        return f"<emphasis level='moderate'>{match.group(0)}</emphasis>"
    return re.sub(r'\b[A-Z]{2,}\b', repl, text)

def add_emotion_tags(text: str, emotion: str = None) -> str:
    """
    Wrap certain keywords with emotional prosody.
    """
    if not emotion: return text
    rate_mod, pitch_mod = EMOTION_MODIFIERS.get(emotion, ("0%", "0%"))
    return f"<prosody rate='{rate_mod}' pitch='{pitch_mod}'>{text}</prosody>"

def parse_laughs(text: str) -> str:
    """
    Detect laughter patterns and convert to prosody.
    """
    return re.sub(r'\b(haha|lol|😂|🤣)\b',
                  r"<prosody rate='+15%'>\1</prosody>", text, flags=re.IGNORECASE)

def parse_whispers(text: str) -> str:
    """
    Detect whisper markers in text and wrap in voice style.
    """
    return re.sub(r'\*whisper\*(.*?)\*endwhisper\*',
                  r"<voice style='whispered'>\1</voice>", text, flags=re.DOTALL)

def parse_shouts(text: str) -> str:
    """
    Detect shouting markers in text and add prosody.
    """
    return re.sub(r'\*shout\*(.*?)\*endshout\*',
                  r"<prosody rate='+15%' pitch='+10%'>\1</prosody>", text, flags=re.DOTALL)

def build_ssml(text: str, state=None, emotion: str = None) -> str:
    """
    Convert plain text into expressive SSML.
    - state: object with .personality and .intimacy (0-10)
    - emotion: optional emotion string
    """
    # Apply personality defaults
    if state and getattr(state, "personality", None) in VOICE_PROFILES:
        rate, pitch, pause = VOICE_PROFILES[state.personality]
        intimacy_boost = getattr(state, "intimacy", 0) * 5
        pitch_final = f"+{int(int(pitch.replace('%','')) + intimacy_boost)}%"
    else:
        rate, pitch_final, pause = "medium", "0%", "200ms"

    # Apply natural humanization
    text = humanize(text)
    text = emphasize_caps(text)
    text = parse_laughs(text)
    text = parse_whispers(text)
    text = parse_shouts(text)

    # Wrap emotion if provided
    text = add_emotion_tags(text, emotion)

    # Final SSML
    ssml = f"""
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <prosody rate="{rate}" pitch="{pitch_final}">
        <break time="{pause}"/>
        {text}
    </prosody>
</speak>
"""
    return ssml
