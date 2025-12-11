import time

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode

from utils.parameters import DEFAULT_AUDIO_LANG, DEFAULT_TRANS_LANG, REFRESH_RATE_FAST, REFRESH_RATE_SLOW
from utils.lang_list import LANGUAGE_CODES
from utils.display import get_html_subt, format_subt, join_text
from utils.streamlit_utils import shutdown_app
from utils.logs import print_logs_threads
from thread_manager import ThreadManager, stop_all_threads
from microphone_stream import AudioProcessor


if st.session_state.get("shutdown", False):
    print_logs_threads("Threads after executing stop_all_threads (close app)")
    st.write("App closed. Press Ctrl+C in the terminal.")
    st.stop()

st.set_page_config(layout="wide")
st.title("Transcription and translation")

col_close, col_rerun, _, _, _, _, _, _, _, _ = st.columns(10, gap=None)
with col_close:
    if st.button("Close App"):
        print_logs_threads("Threads before executing stop_all_threads (close app)")
        shutdown_app()
with col_rerun:
    if st.button("Rerun App"):
        print_logs_threads("Threads before executing stop_all_threads (rerun)")
        stop_all_threads()
        print_logs_threads("Threads after executing stop_all_threads (rerun)")
        st.rerun()


#------- languages choice -------#
lang_keys = list(LANGUAGE_CODES.keys())
st.session_state.setdefault("lang_audio", DEFAULT_AUDIO_LANG)
st.session_state.setdefault("lang_transl", DEFAULT_TRANS_LANG)

col1, col2 = st.columns(2)
with col1:
    lang_audio = st.selectbox("Audio language", lang_keys, key="lang_audio")
with col2:
    lang_transl = st.selectbox("Translation language", lang_keys, key="lang_transl")

LANG_AUDIO = LANGUAGE_CODES[lang_audio]
LANG_TRANSL = LANGUAGE_CODES[lang_transl]


#------- select device -------#
ctx = webrtc_streamer(
    key="audio",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
    async_processing=True,
    audio_receiver_size=128,
)


#------- display init -------#
transc, transl, prev_transc, prev_transl = [], [], [], []
col_transc, col_transl = st.columns(2)
with col_transc:
    transc_box = st.empty()
with col_transl:
    transl_box = st.empty()


#------- stopping speech and translation threads -------#
print_logs_threads("Threads before stop_all_threads (before running while)")
stop_all_threads()
print_logs_threads("Threads after stop_all_threads (before running while)")

if ctx and ctx.audio_processor:

    #------- parallel threads for STT and translation -------#
    st.session_state.threads = ThreadManager(LANG_AUDIO, LANG_TRANSL, ctx.audio_processor)
    print_logs_threads("Threads after creating threads (before running while)")

    threads = st.session_state.threads
    threads.start()


    #----- streamlit display updates -----#
    has_one_line_transc, has_one_line_transl = True, True
    while threads.running:

        new_line_transc, prev_transc, transc = format_subt(threads.output_stt, prev_transc)
        new_line_transl, prev_transl, transl = format_subt(threads.output_transl, prev_transl)

        # transcription
        line_scroll_transc = new_line_transc and not has_one_line_transc
        html_transc = get_html_subt(join_text(prev_transc, LANG_AUDIO), join_text(transc, LANG_AUDIO), line_scroll_transc, subt_type="transc")
        transc_box.markdown(html_transc, unsafe_allow_html=True)

        if new_line_transc and has_one_line_transc:
            has_one_line_transc = False

        waiting_time_transc = REFRESH_RATE_SLOW if line_scroll_transc else REFRESH_RATE_FAST

        # translation
        line_scroll_transl = new_line_transl and not has_one_line_transl
        html_transl = get_html_subt(join_text(prev_transl, LANG_TRANSL), join_text(transl, LANG_TRANSL), line_scroll_transl, subt_type="transl")
        transl_box.markdown(html_transl, unsafe_allow_html=True)

        if new_line_transl and has_one_line_transl:
            has_one_line_transl = False

        waiting_time_transl = REFRESH_RATE_SLOW if line_scroll_transl else REFRESH_RATE_FAST

        # waiting time
        time.sleep(max(waiting_time_transc, waiting_time_transl))
