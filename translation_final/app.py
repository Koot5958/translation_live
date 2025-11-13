import time
import gc

import numpy as np
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import torch

from utils.lang_list import LANGUAGE_CODES
from utils.display import update_boxes
from translation import translate, transcribe, load_models
from audio_processor import AudioProcessor


STEP = 3
OVERLAP_PAST = 1
OVERLAP_FUTURE = 0.2

st.set_page_config(layout="wide")
st.title("Transcription and translation")


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
    key="audio-level",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
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

    while ctx.state.playing:
        buffer = ctx.audio_processor.pop_buffer()

        if len(buffer) == 0:
            continue

        if prev_buffer is None or len(prev_buffer) == 0:
            segment = buffer
            transc = transcribe(segment, 0, (1 - OVERLAP_FUTURE) * len(buffer))
            last_step = len(buffer)
        else:
            segment = np.concatenate([buffer, prev_buffer])
            curr_step = len(segment) // 2
            segment = segment[(1 - OVERLAP_PAST) * curr_step :]

            start_subt = max(0, OVERLAP_PAST * curr_step - OVERLAP_FUTURE * last_step)
            end_subt = (2 - OVERLAP_FUTURE) * curr_step
            print("start/end subt ", start_subt, end_subt, len(segment))
            transc = transcribe(segment, start_subt, end_subt)
            last_step = curr_step

        transl = translate(transc, LANG_SUBTITLES)

        update_boxes(transc_box, transl_box, prev_transc, transc, prev_transl, transl)

        prev_transc = transc
        prev_transl = transl
        prev_buffer = buffer

        del buffer, transc, segment
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        time.sleep(STEP)

