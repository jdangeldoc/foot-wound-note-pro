import os
from openai import OpenAI

# Initialize modern OpenAI client (OpenAI SDK 1.x)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def tts_mp3(text: str, voice: str = "verse") -> bytes:
    """Text-to-speech to MP3 using gpt-4o-mini-tts."""
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        format="mp3",
    )
    return response.read()

def stt_from_bytes(audio_bytes: bytes, mime: str = "audio/mp3") -> str:
    """Speech-to-text from bytes using Whisper."""
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.mp3", audio_bytes, mime),
    )
    return response.text
