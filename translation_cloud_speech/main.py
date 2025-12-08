import streamlit as st
import time

from utils.lang_list import LANGUAGE_CODES
from utils.display import get_html_subt
from thread_manager import ThreadManager


st.set_page_config(layout="wide")
st.title("Transcription and translation")


#------- languages choice -------#
col1, col2 = st.columns(2)
lang_keys = list(LANGUAGE_CODES.keys())
with col1:
    lang_audio = st.selectbox("Audio language", list(LANGUAGE_CODES.keys()), index=lang_keys.index("French (France)"))
with col2:
    lang_subtitles = st.selectbox("Translation language", list(LANGUAGE_CODES.keys()), index=lang_keys.index("English (United States)"))
LANG_AUDIO = LANGUAGE_CODES[lang_audio]
LANG_SUBTITLES = LANGUAGE_CODES[lang_subtitles]


#------- display init -------#
transc, transl, prev_transc, prev_transc = [], [], [], []
transc_box, transl_box = st.empty(), st.empty()
max_len = 10


#------- parallel threads for STT and translation -------#
threads = ThreadManager(lang_audio=LANG_AUDIO, lang_subt=LANG_SUBTITLES)
threads.start()


#----- streamlit display updates -----#
has_one_line = True
while True:
    # update languages
    threads.lang_audio = LANG_AUDIO
    threads.lang_subt = LANG_SUBTITLES

    transc_split = threads.output_stt.split()
    new_line = False

    if len(transc_split) <= max_len:
        transc = transc_split
    else:
        transc = transc_split[(len(transc_split) // max_len) * max_len :]
        start_transc = len(transc_split) - len(transc)
        if prev_transc != (transc_split[: start_transc])[-max_len :]:
            prev_transc = (transc_split[: start_transc])[-max_len :]
            new_line = True

    line_scroll = new_line and not has_one_line
    html = get_html_subt(prev_transc, transc, line_scroll)
    transc_box.markdown(html, unsafe_allow_html=True)

    if new_line and has_one_line:
        has_one_line = False

    waiting_time = 0.3 if line_scroll else 0.05
    time.sleep(waiting_time)
