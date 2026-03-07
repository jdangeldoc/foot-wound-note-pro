VOICE I/O FIX BUNDLE

Files included:
- wound_voice/voice_io.py
- core/voice_io.py

Use ONE of these placements based on your imports.
If your Streamlit page imports:
    from wound_voice import render_wound_voice
    from voice_io import tts_mp3, stt_from_bytes   <-- legacy style
then KEEP the 'core/voice_io.py' copy.

If your page imports:
    from wound_voice.voice_io import tts_mp3, stt_from_bytes
then KEEP the 'wound_voice/voice_io.py' copy.

You may keep both; Python will load whichever path your code requests.
Both files are identical and target OpenAI SDK 1.x.
