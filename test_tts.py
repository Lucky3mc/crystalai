import asyncio
import edge_tts

async def main():
    communicate = edge_tts.Communicate(
        "Hello world! Testing TTS",
        voice="en-US-JennyNeural"
    )
    await communicate.save("test.mp3")

asyncio.run(main())
print("Saved test.mp3 successfully")
