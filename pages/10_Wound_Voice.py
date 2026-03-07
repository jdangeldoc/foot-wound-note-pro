import streamlit as st
from wound_voice.voice_io import tts_mp3, stt_from_bytes

def render_wound_voice():
    st.title("Wound Voice Input")
    st.write("Speak into the microphone or upload an audio file.")

    uploaded_file = st.file_uploader("Upload audio (mp3/wav)", type=["mp3", "wav"])
    if uploaded_file is not None:
        audio_bytes = uploaded_file.read()
        st.audio(audio_bytes)  # let Streamlit sniff the format
        with st.spinner("Transcribing..."):
            text = stt_from_bytes(audio_bytes)
        st.success("Transcription complete!")
        st.text_area("Transcript", value=text, height=200)

    user_text = st.text_input("Or enter text to synthesize:")
    if st.button("Generate Voice"):
        if user_text.strip():
            with st.spinner("Generating voice..."):
                audio_out = tts_mp3(user_text)
            st.audio(audio_out)  # no explicit format
        else:
            st.warning("Please enter text first.")

if __name__ == "__main__":
    render_wound_voice()
