# -*- coding: utf-8 -*-
"""
Voice IO utilities for OrthoCoder Pro (OpenAI SDK 1.x compatible).
- Text-to-Speech (TTS) -> MP3 bytes
- Speech-to-Text (STT) from bytes
"""
import os
from openai import OpenAI

# Create client from environment. Do NOT pass proxies or legacy options.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def tts_mp3(text: str, voice: str = "alloy") -> bytes:
    """
    Convert text to speech (mp3) using OpenAI 1.x TTS.
    Returns raw MP3 bytes.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("tts_mp3: 'text' must be a non-empty string")

    resp = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text.strip(),
        format="mp3",
    )
    return resp.read()

def stt_from_bytes(audio_bytes: bytes, mime: str = "audio/mpeg") -> str:
    """
    Transcribe audio bytes using Whisper via OpenAI 1.x.
    mime examples: 'audio/mpeg', 'audio/wav', 'audio/webm'
    """
    if not audio_bytes:
        raise ValueError("stt_from_bytes: 'audio_bytes' is empty")

    # OpenAI 1.x accepts a (filename, bytes, mimetype) tuple for in-memory files.
    resp = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio_input." + (mime.split("/")[-1] or "mp3"), audio_bytes, mime),
    )
    return resp.text or ""
