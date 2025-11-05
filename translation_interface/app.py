import time

import streamlit as st

from translation import PreProcessed, transcribe, translate, load_models
from lang_list import LANGUAGE_CODES
from display import update_boxes


STEP = 4
OVERLAP = 5

st.set_page_config(layout="wide")
st.title("Transcription and translation")

#------- upload audio file -------#
uploaded = st.file_uploader("Upload audio file", type=["mp3", "wav"])
if not uploaded:
    st.stop()

preprocessed = PreProcessed(uploaded)
audio_len = len(preprocessed.raw_data) / preprocessed.sr


#------- languages choice -------#
col1, col2 = st.columns(2)
with col1:
    lang_audio = st.selectbox("Audio language", list(LANGUAGE_CODES.keys()), index=0)
with col2:
    lang_subtitles = st.selectbox("Translation language", list(LANGUAGE_CODES.keys()), index=1)
LANG_AUDIO = LANGUAGE_CODES[lang_audio]
LANG_SUBTITLES = LANGUAGE_CODES[lang_subtitles]


#------- load models -------#
if "models_loaded" not in st.session_state:
    st.session_state.models_loaded = False
if "models_info" not in st.session_state:
    st.session_state.models_info = None

col_load, col_play = st.columns([1, 2])
with col_load:
    if st.button("Load models for selected languages"):
        with st.spinner("Loading models..."):
            st.session_state.models_info = load_models(LANG_AUDIO)
            st.session_state.models_loaded = True
        st.success("Models loaded for: " + lang_audio + " to " + lang_subtitles)


#------- displays initialization -------#
with col_play:
    play_start = st.button("Play audio")

col_left, col_right = st.columns(2)
transc_box = col_left.empty()
transl_box = col_right.empty()
progress_bar = st.progress(0)
status_text = st.empty()

update_boxes(transc_box, transl_box, None, None, None, None)


#------- run audio -------#
if play_start and not st.session_state.get("running", False):
    st.session_state.running = True

if st.session_state.get("running", False):
    st.audio(
        uploaded, 
        format="audio/mpeg" if uploaded.name.endswith(".mp3") else "audio/wav",
        autoplay=True,
    )

    playback_start = time.time()
    time_pos = 0.0

    prev_transc, prev_transl = None, None

    while time_pos < audio_len:
        start_time = max(0.0, time_pos + STEP - (STEP + OVERLAP))
        end_time = min(time_pos + STEP, audio_len)

        segment = preprocessed.norm_data(start_time, end_time)

        # compute transcription and translation
        gen_start = time.time()
        transc = transcribe(segment, max(min(OVERLAP, time_pos), 0.0))
        transl = translate(transc, LANG_SUBTITLES) if transc else ""
        gen_time = time.time() - gen_start

        # wait before display
        display_at = playback_start + end_time + gen_time
        while time.time() < display_at:
            time.sleep(0.05)

        # update displays
        update_boxes(transc_box, transl_box, prev_transc, transc, prev_transl, transl)
        prev_transc = transc
        prev_transl = transl

        progress_bar.progress(min(end_time / audio_len, 1.0))
        status_text.text(f"Segment {end_time-STEP}s-{end_time}s — printed at {end_time + gen_time:.1f}s (generation duration {gen_time:.2f}s)")

        # update time
        time_pos += STEP

    progress_bar.progress(1.0)
    st.session_state.running = False
