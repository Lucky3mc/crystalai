import threading
import tempfile
import asyncio
import os
import time
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import edge_tts
from voice_ssml import build_ssml  # Your SSML builder module

# === FFmpeg paths ===
FFMPEG_BIN = r"C:\Users\user\Documents\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
FFPROBE_BIN = r"C:\Users\user\Documents\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"

AudioSegment.converter = FFMPEG_BIN
AudioSegment.ffprobe = FFPROBE_BIN

# === Globals ===
_stop_flag = False
_lock = threading.Lock()


def stop_speaking():
    """Stop any currently playing speech."""
    global _stop_flag
    _stop_flag = True


def speak(text: str, state=None, emotion=None):
    """
    Speak text asynchronously using Edge-TTS.
    Supports personality via 'state' and emotions: happy/laugh, whisper, shout/angry.
    """
    def run(local_text, local_emotion):
        global _stop_flag

        with _lock:
            # Stop previous speech
            _stop_flag = True
            _stop_flag = False

            # Parse emotion markers
            if "*laugh*" in local_text:
                local_emotion = "happy"
                local_text = local_text.replace("*laugh*", "")
            elif "*whisper*" in local_text:
                local_emotion = "whisper"
                local_text = local_text.replace("*whisper*", "")
            elif "*shout*" in local_text:
                local_emotion = "angry"
                local_text = local_text.replace("*shout*", "")

            if local_emotion:
                print(f"[TTS] Speaking with emotion: {local_emotion}")

            # Build SSML
            ssml = build_ssml(local_text, state) if state else f"<speak>{local_text}</speak>"

            # Edge-TTS voice
            voice = "en-US-JennyNeural"

            # Temporary MP3 file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_path = f.name

            try:
                # Generate TTS
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(edge_tts.Communicate(ssml, voice).save(temp_path))
                loop.close()

                # Check if file exists
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    print("[TTS] No audio file generated.")
                    return

                # Play audio
                audio = AudioSegment.from_file(temp_path, format="mp3")
                play_obj = _play_with_simpleaudio(audio)
                while play_obj.is_playing() and not _stop_flag:
                    time.sleep(0.1)
                if _stop_flag:
                    play_obj.stop()

            except Exception as e:
                print("[TTS] Playback Error:", e)
            finally:
                # Cleanup
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    # Start TTS in a daemon thread
    threading.Thread(target=run, args=(text, emotion), daemon=True).start()
