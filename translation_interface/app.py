# app.py
import streamlit as st
import streamlit.components.v1 as components
import time
import base64
from translation import PreProcessed, transcribe, translate, load_models
from lang_list import LANGUAGE_CODES


STEP = 4
OVERLAP = 2

st.set_page_config(layout="wide")
st.title("Transcription and translation")

uploaded = st.file_uploader("Upload audio file", type=["mp3", "wav"])
if not uploaded:
    st.info("Upload an audio file to start.")
    st.stop()

tmp_path = "temp_audio.mp3"
with open(tmp_path, "wb") as f:
    f.write(uploaded.read())

with open(tmp_path, "rb") as f:
    audio_bytes = f.read()
b64 = base64.b64encode(audio_bytes).decode("utf-8")
mime = "audio/mpeg" if tmp_path.lower().endswith(".mp3") else "audio/wav"
data_uri = f"data:{mime};base64,{b64}"

pre = PreProcessed(tmp_path)
audio_len = len(pre.raw_data) / pre.sr

# lang choice
col1, col2 = st.columns(2)
with col1:
    lang_audio = st.selectbox("Audio language", list(LANGUAGE_CODES.keys()), index=0)
with col2:
    lang_subtitles = st.selectbox("Translation language", list(LANGUAGE_CODES.keys()), index=1)
LANG_AUDIO = LANGUAGE_CODES[lang_audio]
LANG_SUBTITLES = LANGUAGE_CODES[lang_subtitles]

if "running" not in st.session_state:
    st.session_state.running = False

play_start = st.button("Play audio")

col_left, col_right = st.columns(2)
transcript_box = col_left.empty()
translation_box = col_right.empty()
progress_bar = st.progress(0)
status_text = st.empty()

transcript_box.markdown(
    """
        <div style="font-size:1.1em;">
            <h2>Transcript</h2>
        </div>
        <p style="color:gray; opacity:0.6; margin-bottom:0.2em;">...</p>
        <p style="background-color:#1E90FF22; padding:4px 8px; border-radius:6px;">Waiting for transcription...</p>
    """,
    unsafe_allow_html=True,
)
translation_box.markdown(
    """
        <div style="font-size:1.1em;">
            <h2>Translation</h2>
        </div>
        <p style="color:gray; opacity:0.6; margin-bottom:0.2em;">...</p>
        <p style="background-color:#1E90FF22; padding:4px 8px; border-radius:6px;">Waiting for translation...</p>
    """,
    unsafe_allow_html=True,
)

if play_start and not st.session_state.running:
    st.session_state.running = True

if st.session_state.running:
    audio_html = (
        f'<audio id="player" controls autoplay>'
        f'  <source src="{data_uri}" type="{mime}">'
        f'  Your browser does not support the audio element.'
        f'</audio>'
        f'<script>document.getElementById("player").play().catch(()=>{{}});</script>'
    )
    components.html(audio_html, height=80)

    playback_start = time.time()
    time_pos = 0.0
    idx = 0
    # nombre de segments
    n_segments = int((audio_len + STEP - 1e-9) // STEP) + (1 if (audio_len % STEP) > 1e-9 else 0)

    last_transcript = "..."
    last_translation = "..."

    while time_pos < audio_len:
        start_time = max(0.0, time_pos + STEP - (STEP + OVERLAP))
        end_time = min(time_pos + STEP, audio_len)

        segment = pre.norm_data(start_time, end_time)

        gen_start = time.time()
        text = transcribe(segment, max(min(OVERLAP, time_pos), 0.0))
        translated = translate(text, LANG_SUBTITLES) if text else ""
        gen_time = time.time() - gen_start

        display_at = playback_start + end_time + gen_time
        while time.time() < display_at:
            time.sleep(0.03)

        transcript_box.markdown(
            f"""
            <div style="font-size:1.1em;">
                <h2>Transcript</h2>
                <p style="color:gray; opacity:0.6; margin-bottom:0.2em;">
                    {last_transcript}
                </p>
                <p style="background-color:#1E90FF22; padding:4px 8px; border-radius:6px;">
                    <b>{text}</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        last_transcript = text

        translation_box.markdown(
            f"""
            <div style="font-size:1.1em;">
                <h2>Translation</h2>
                <p style="color:gray; opacity:0.6; margin-bottom:0.2em;">
                    {last_translation}
                </p>
                <p style="background-color:#1E90FF22; padding:4px 8px; border-radius:6px;">
                    <b>{translated}</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        last_translation = translated

        progress_bar.progress(min(end_time / audio_len, 1.0))
        status_text.text(f"Segment {idx+1}/{n_segments} — printed at {end_time + gen_time:.1f}s (generation duration {gen_time:.2f}s)")

        idx += 1
        time_pos += STEP

    progress_bar.progress(1.0)
    st.session_state.running = False
