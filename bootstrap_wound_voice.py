# bootstrap_wound_voice.py
# One-shot installer for the Wound Voice page.

import os, sys, shutil, zipfile, time
from pathlib import Path

NEEDED_REQ = [
    "streamlit==1.36.0",
    "streamlit-webrtc==0.47.7",
    "pydub==0.25.1",
    "soundfile==0.12.1",
    "numpy==1.26.4",
    "openai==1.43.1",
]

VOICE_IO = r'''import io, os
from pydub import AudioSegment
from openai import OpenAI

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def tts_mp3(text: str, voice: str | None = None) -> bytes:
    voice = voice or os.getenv("AUDIO_VOICE", "alloy")
    resp = _client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        format="mp3",
    )
    data = getattr(resp, "content", None) or getattr(resp, "read", lambda: b"")()
    if not data:
        raise RuntimeError("TTS returned empty audio.")
    return data

def stt_from_bytes(raw_audio: bytes, fmt: str = "wav") -> str:
    audio = AudioSegment.from_file(io.BytesIO(raw_audio), format=fmt).set_frame_rate(16000).set_channels(1)
    buf = io.BytesIO(); audio.export(buf, format="wav"); buf.seek(0)
    tr = _client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("speech.wav", buf, "audio/wav")
    )
    return (getattr(tr, "text", "") or "").strip()
'''

WOUND_VOICE = r'''from typing import Dict, List
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av, numpy as np, io, soundfile as sf
from voice_io import tts_mp3, stt_from_bytes

QUESTIONS: List[Dict] = [
    {"key": "site",         "q": "Which body site? For example, right plantar forefoot."},
    {"key": "depth",        "q": "Deepest tissue treated: skin, subcutaneous, fascia, muscle, or bone?"},
    {"key": "size_cm2",     "q": "Total surface area in square centimeters?"},
    {"key": "vascularity",  "q": "Vascularity: good or poor?"},
    {"key": "infection",    "q": "Is the wound infected? Say yes or no."},
    {"key": "instruments",  "q": "Which instruments did you use? For example scalpel, curette, rongeur, or scissors."},
]

def _init_state():
    return {"active": False, "i": 0, "answers": {q["key"]: "" for q in QUESTIONS}, "buf": bytearray()}

def render_wound_voice(form_data: Dict) -> Dict:
    if "wvoice" not in st.session_state:
        st.session_state.wvoice = _init_state()
    S = st.session_state.wvoice

    st.markdown("### 🎙️ Wound Voice Interview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Start", disabled=S["active"]):
            st.session_state.wvoice = _init_state(); S = st.session_state.wvoice; S["active"] = True
    with c2:
        if st.button("Stop", disabled=not S["active"]):
            S["active"] = False
    with c3:
        if st.button("Repeat Q", disabled=not S["active"]):
            pass
    with c4:
        if st.button("Clear All"):
            st.session_state.wvoice = _init_state(); S = st.session_state.wvoice

    if S["active"]:
        try:
            st.audio(tts_mp3(QUESTIONS[S["i"]]["q"]), format="audio/mp3")
        except Exception as e:
            st.error(f"TTS error: {e}")

        class AudioSink:
            def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
                pcm = frame.to_ndarray().mean(axis=0).astype(np.float32).tobytes()
                S["buf"].extend(pcm)
                return frame

        webrtc_streamer(
            key=f"wound-voice-{S['i']}",
            mode=WebRtcMode.SENDRECV,
            audio_receiver_size=256,
            video_receiver_size=0,
            media_stream_constraints={"video": False, "audio": True},
            async_processing=True,
        )

        a, b = st.columns(2)
        with a:
            if st.button("Stop & Transcribe"):
                pcm = bytes(S["buf"]); S["buf"] = bytearray()
                if len(pcm) < 16000:
                    st.warning("Audio too short — answer again.")
                else:
                    buf = io.BytesIO()
                    arr = np.frombuffer(pcm, dtype=np.float32)
                    sf.write(buf, arr, 16000, format="WAV", subtype="PCM_16")
                    wav = buf.getvalue()
                    try:
                        text = stt_from_bytes(wav, fmt="wav")
                        if text:
                            key = QUESTIONS[S["i"]]["key"]
                            S["answers"][key] = text
                            st.success(f"{key}: {text}")
                            if S["i"] < len(QUESTIONS) - 1:
                                S["i"] += 1
                            else:
                                st.success("Interview complete.")
                        else:
                            st.warning("No speech detected.")
                    except Exception as e:
                        st.error(f"Transcription error: {e}")
        with b:
            if st.button("Next without voice"):
                if S["i"] < len(QUESTIONS) - 1:
                    S["i"] += 1

    with st.expander("Captured answers", expanded=False):
        st.json(S["answers"])

    ans = S["answers"]
    if ans.get("site"):        form_data["site"] = ans["site"]
    if ans.get("depth"):       form_data["depth"] = ans["depth"]
    if ans.get("size_cm2"):    form_data["size_cm2"] = ans["size_cm2"]
    form_data["vascularity"] = (ans.get("vascularity") or form_data.get("vascularity") or "Good").title()
    if ans.get("infection"):
        v = ans["infection"].strip().lower()
        form_data["infection"] = "Yes" if v.startswith("y") else ("No" if v.startswith("n") else form_data.get("infection", "No"))
    if ans.get("instruments"): form_data["instruments"] = ans["instruments"]
    return form_data
'''

VOICE_PAGE = r'''import streamlit as st
from wound_voice import render_wound_voice

st.title("🎙️ Voice-Driven Wound Interview")

wound_form = {
    "site": "",
    "depth": "",
    "size_cm2": "",
    "vascularity": "Good",
    "infection": "No",
    "instruments": "",
}

wound_form = render_wound_voice(wound_form)

st.subheader("Captured Answers")
st.json(wound_form)

if st.button("Generate Note & Codes"):
    note = f"Debridement at {wound_form['site']} to {wound_form['depth']} ({wound_form['size_cm2']} cm²). " \
           f"Vascularity {wound_form['vascularity']}. Infection {wound_form['infection']}. " \
           f"Instruments {wound_form['instruments']}."
    cpt = "11042"
    icd = "L97.509"
    st.text_area("Operative Note", note, height=220)
    st.write("**CPT:**", cpt)
    st.write("**ICD-10:**", icd)
'''

def main():
    root = Path.cwd().resolve()
    print(f"[ROOT] Using: {root}")

    # Make sure we're at the folder with app.py
    if not (root / "app.py").exists():
        print("[ERROR] app.py not found here. Open the correct folder and run again.")
        sys.exit(1)

    # Write helper files
    (root / "voice_io.py").write_text(VOICE_IO, encoding="utf-8")
    print("[WRITE] voice_io.py")

    (root / "wound_voice.py").write_text(WOUND_VOICE, encoding="utf-8")
    print("[WRITE] wound_voice.py")

    pages = root / "pages"
    pages.mkdir(exist_ok=True)
    (pages / "10_Wound_Voice.py").write_text(VOICE_PAGE, encoding="utf-8")
    print("[WRITE] pages\\10_Wound_Voice.py")

    # requirements.txt
    req = root / "requirements.txt"
    if req.exists():
        lines = req.read_text(encoding="utf-8").splitlines()
    else:
        lines = []
    bases = {l.split("==")[0].lower() for l in lines if "==" in l}
    for pkg in NEEDED_REQ:
        base = pkg.split("==")[0].lower()
        if base not in bases:
            lines.append(pkg)
    req.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[UPDATE] requirements.txt")

    print("\nNext:")
    print('1) Set your API key (once):  setx OPENAI_API_KEY "sk-...yourkey..."  then close/reopen terminal')
    print("2) Install deps:             pip install -r requirements.txt")
    print("3) Run app:                  streamlit run app.py")
    print("4) In the left sidebar: Pages → 🎙️ Voice-Driven Wound Interview")

if __name__ == "__main__":
    main()
