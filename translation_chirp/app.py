import time
import os

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode

from utils.lang_list import LANGUAGE_CODES
from utils.logs.logs import log_memory
from translation import google_streaming_stt
from audio_processor import AudioProcessor


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

#------- running process -------#
if ctx and ctx.audio_processor:
    st.write("Waiting for transcription...")

    print("t3")
    while ctx.state.playing:
        for transcript in google_streaming_stt(ctx):
            print("t2")
            log_memory()
            duration = time.time()
            transc_box.markdown("**" + transcript + "**")
            duration = time.time() - duration
            log_memory()

