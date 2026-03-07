import os, inspect, sys
from openai import OpenAI

# --- Diagnostics (prints once in Streamlit console) ---
print("[voice_io] module file:", __file__)
try:
    import httpx, openai as _oai
    print(f"[voice_io] httpx={getattr(httpx,'__version__','?')} openai={getattr(_oai,'__version__','?')}")
except Exception as _e:
    print("[voice_io] diag import failed:", _e)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError('OPENAI_API_KEY is not set. In PowerShell run: setx OPENAI_API_KEY "sk-..." then reopen.')

client = OpenAI(api_key=api_key)

def _read_bytes(resp):
    """Return raw bytes from response across SDK variants."""
    if hasattr(resp, "read") and callable(resp.read):
        return resp.read()
    if hasattr(resp, "content"):
        return resp.content
    if hasattr(resp, "getvalue"):
        return resp.getvalue()
    try:
        return bytes(resp)
    except Exception as e:
        raise RuntimeError(f"Unable to read audio bytes from TTS response: {e}")

def tts_mp3(text: str, voice: str = "verse") -> bytes:
    """
    Generate speech audio bytes from text.
    Uses streaming API when available; never passes a 'format' argument.
    """
    # Preferred: streaming
    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
        ) as resp:
            return _read_bytes(resp)
    except Exception as e:
        print("[voice_io] streaming TTS not available, falling back:", type(e).__name__, e)

    # Fallback: non-streaming (no 'format' kwarg)
    resp = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
    )
    return _read_bytes(resp)

def stt_from_bytes(audio_bytes: bytes, mime: str = "audio/mp3") -> str:
    """Transcribe audio bytes to text via Whisper."""
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.mp3", audio_bytes, mime),
    )
    return response.text
