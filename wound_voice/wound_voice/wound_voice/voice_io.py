import os
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError('OPENAI_API_KEY is not set. In PowerShell run: setx OPENAI_API_KEY "sk-..." then reopen.')

client = OpenAI(api_key=api_key)

def _read_bytes(resp):
    """
    Return raw bytes from various response types across SDK sub-versions.
    """
    # Streaming context returns object with .read()
    if hasattr(resp, "read") and callable(resp.read):
        return resp.read()
    # Some responses may have .content / .getvalue()
    if hasattr(resp, "content"):
        return resp.content
    if hasattr(resp, "getvalue"):
        return resp.getvalue()
    # Fallback: try to bytes() it
    try:
        return bytes(resp)
    except Exception:
        raise RuntimeError("Unable to read audio bytes from TTS response.")

def tts_mp3(text: str, voice: str = "verse") -> bytes:
    """
    Generate speech audio bytes from text.
    Prefer the streaming API (no 'format' arg). Fall back to non-streaming if needed.
    """
    # Primary path: streaming API (modern)
    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
        ) as resp:
            return _read_bytes(resp)
    except AttributeError:
        # Older 1.x variants may not expose with_streaming_response
        pass
    except TypeError:
        # Any signature mismatch: try fallback
        pass

    # Fallback path: non-streaming create without 'format' (SDKs where it exists)
    resp = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
    )
    return _read_bytes(resp)

def stt_from_bytes(audio_bytes: bytes, mime: str = "audio/mp3") -> str:
    """
    Transcribe audio bytes to text via Whisper.
    """
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.mp3", audio_bytes, mime),
    )
    return response.text
