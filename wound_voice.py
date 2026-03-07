from typing import Dict, List
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av, numpy as np, io, soundfile as sf
from voice_io import tts_mp3, stt_from_bytes
QUESTIONS: List[Dict] = [
    {"key":"site","q":"Which body site? For example, right plantar forefoot."},
    {"key":"depth","q":"Deepest tissue treated: skin, subcutaneous, fascia, muscle, or bone?"},
    {"key":"size_cm2","q":"Total surface area in square centimeters?"},
    {"key":"vascularity","q":"Vascularity: good or poor?"},
    {"key":"infection","q":"Is the wound infected? Say yes or no."},
    {"key":"instruments","q":"Which instruments did you use? For example scalpel, curette, rongeur, or scissors."},
]
def _init_state(): return {"active": False, "i": 0, "answers": {q["key"]:"" for q in QUESTIONS}, "buf": bytearray()}
def render_wound_voice(form_data: Dict) -> Dict:
    if "wvoice" not in st.session_state: st.session_state.wvoice = _init_state()
    S = st.session_state.wvoice
    st.markdown("### 🎙️ Wound Voice Interview")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if st.button("Start", disabled=S["active"]):
            st.session_state.wvoice = _init_state(); S = st.session_state.wvoice; S["active"]=True
    with c2:
        if st.button("Stop", disabled=not S["active"]): S["active"]=False
    with c3:
        if st.button("Repeat Q", disabled=not S["active"]): pass
    with c4:
        if st.button("Clear All"): st.session_state.wvoice = _init_state(); S = st.session_state.wvoice
    if S["active"]:
        try: st.audio(tts_mp3(QUESTIONS[S["i"]]["q"]), format="audio/mp3")
        except Exception as e: st.error(f"TTS error: {e}")
        webrtc_streamer(key=f"wound-voice-{S['i']}", mode=WebRtcMode.SENDRECV,
                        audio_receiver_size=256, video_receiver_size=0,
                        media_stream_constraints={"video": False, "audio": True}, async_processing=True)
        a,b = st.columns(2)
        with a:
            if st.button("Stop & Transcribe"):
                pcm = bytes(S["buf"]); S["buf"]=bytearray()
                if len(pcm) < 16000: st.warning("Audio too short — answer again.")
                else:
                    buf = io.BytesIO(); arr = np.frombuffer(pcm, dtype=np.float32)
                    sf.write(buf, arr, 16000, format="WAV", subtype="PCM_16"); wav = buf.getvalue()
                    try:
                        text = stt_from_bytes(wav, fmt="wav")
                        if text:
                            key = QUESTIONS[S["i"]]["key"]; S["answers"][key]=text; st.success(f"{key}: {text}")
                            if S["i"] < len(QUESTIONS)-1: S["i"] += 1
                            else: st.success("Interview complete.")
                        else: st.warning("No speech detected.")
                    except Exception as e: st.error(f"Transcription error: {e}")
        with b:
            if st.button("Next without voice") and S["i"] < len(QUESTIONS)-1: S["i"] += 1
    with st.expander("Captured answers", expanded=False): st.json(S["answers"])
    ans = S["answers"]
    if ans.get("site"): form_data["site"]=ans["site"]
    if ans.get("depth"): form_data["depth"]=ans["depth"]
    if ans.get("size_cm2"): form_data["size_cm2"]=ans["size_cm2"]
    form_data["vascularity"] = (ans.get("vascularity") or form_data.get("vascularity") or "Good").title()
    if ans.get("infection"):
        v = ans["infection"].strip().lower()
        form_data["infection"] = "Yes" if v.startswith("y") else ("No" if v.startswith("n") else form_data.get("infection","No"))
    if ans.get("instruments"): form_data["instruments"]=ans["instruments"]
    return form_data
