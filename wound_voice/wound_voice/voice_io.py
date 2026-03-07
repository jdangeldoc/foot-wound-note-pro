import os
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set. In PowerShell run: setx OPENAI_API_KEY \"sk-...\" then reopen the terminal.")

client = OpenAI(api_key=api_key)

def tts_mp3(text: str, voice: str = "verse") -> bytes:
    """
    Generate speech audio bytes from text using the 1.x SDK.
    The 'format' parameter has been removed in recent SDKs.
    We use the streaming response which returns raw audio bytes.
    """
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
    ) as resp:
        audio_bytes = resp.read()
    return audio_bytes

def stt_from_bytes(audio_bytes: bytes, mime: str = "audio/mp3") -> str:
    """
    Transcribe audio bytes to text.
    """
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.mp3", audio_bytes, mime),
    )
    return response.text
