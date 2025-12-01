import time
import os

import numpy as np
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import torch

from utils.lang_list import LANGUAGE_CODES
from utils.display import update_boxes
from utils.parameters import SR, STEP, OVERLAP_FUTURE, OVERLAP_PAST
from utils.logs.logs import log_memory, TIME
from utils.logs.save_graph_durations import save_durations_plot
from translation import translate, transcribe, load_models
from audio_processor import AudioProcessor, normalize_buffer


st.set_page_config(layout="wide")
st.title("Transcription and translation")

os.environ["PYTORCH_ALLOC_CONF"] = "max_split_size_mb:20,garbage_collection_threshold:0.6,reserve_alignment:128"


#------- languages choice -------#
col1, col2 = st.columns(2)
lang_keys = list(LANGUAGE_CODES.keys())
with col1:
    lang_audio = st.selectbox("Audio language", list(LANGUAGE_CODES.keys()), index=lang_keys.index("French"))
with col2:
    lang_subtitles = st.selectbox("Translation language", list(LANGUAGE_CODES.keys()), index=lang_keys.index("English"))
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

#------- select device -------#
ctx = webrtc_streamer(
    key="audio",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
    async_processing=True,
    audio_receiver_size=256,
)

#------- displays initialization -------#
col_left, col_right = st.columns(2)
transc_box = col_left.empty()
transl_box = col_right.empty()

update_boxes(transc_box, transl_box, None, None, None, None)

#------- running process -------#
if ctx and ctx.audio_processor:
    start = time.time()
    prev_transc, prev_transl, prev_buffer = None, None, None
    prev_step = start

    durations_transc = []
    durations_transl = []

    while ctx.state.playing:
        if time.time() - prev_step < STEP:
            time.sleep(0.1)
            continue
        prev_step = time.time()

        buffer = ctx.audio_processor.pop_buffer()
        if len(buffer) == 0:
            time.sleep(0.1)
            continue

        log_memory()

        duration_transc = time.time()

        if prev_buffer is None or len(prev_buffer) == 0:
            segment = normalize_buffer(buffer, target_mean=0.1)
            transc = transcribe(segment, 0, ((1 - OVERLAP_FUTURE) * len(buffer)) / SR)
            last_step = len(buffer)
        else:
            segment = np.concatenate([prev_buffer, buffer])
            segment = normalize_buffer(segment, target_mean=0.1)
            curr_step = len(segment) // 2
            segment = segment[(1 - OVERLAP_PAST) * curr_step :]

            start_subt = max(0, OVERLAP_PAST * curr_step - OVERLAP_FUTURE * last_step)
            end_subt = (2 - OVERLAP_FUTURE) * curr_step
            transc = transcribe(segment, start_subt / SR, end_subt / SR)
            last_step = curr_step

        duration_transc = time.time() - duration_transc
        durations_transc.append(duration_transc)

        duration_transl = time.time()
        transl = translate(transc, LANG_SUBTITLES)
        duration_transl = time.time() - duration_transl
        durations_transl.append(duration_transl)

        update_boxes(transc_box, transl_box, prev_transc, transc, prev_transl, transl)

        prev_transc = transc
        prev_transl = transl
        prev_buffer = buffer

        log_memory()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        log_memory()

    save_durations_plot(durations_transc, durations_transl, f"durations_log_{TIME}")

