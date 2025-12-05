import streamlit as st
import threading
import time

from google.cloud import speech

from utils.lang_list import LANGUAGE_CODES
from microphone_stream import CHUNK, RATE, MicrophoneStream


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
transcript = ""
subt = []
max_len = 10
text_area = st.empty()


#------- config initialisation -------#
client = speech.SpeechClient()
config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=RATE,
    language_code=LANG_AUDIO,
    enable_word_time_offsets=True,
)

streaming_config = speech.StreamingRecognitionConfig(
    config=config,
    interim_results=True,
)

#------- running process -------#
def stt_thread_target():
    """Thread où Google STT tourne en arrière-plan."""
    global transcript
    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        responses = client.streaming_recognize(streaming_config, requests)
        for response in responses:
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript


#----- thread STT -----#
stt_thread = threading.Thread(target=stt_thread_target, daemon=True)
stt_thread.start()


#----- streamlit updates -----#
first_new_line = True
while True:
    transc_split = transcript.split()
    new_line = False

    if len(transc_split) <= max_len:
        subt = transc_split
        prev_subt = ""
    else:
        subt = transc_split[(len(transc_split) // max_len) * max_len :]
        start_subt = len(transc_split) - len(subt)
        if prev_subt != (transc_split[: start_subt])[-max_len :]:
            prev_subt = (transc_split[: start_subt])[-max_len :]
            new_line = True

    if new_line:
        if first_new_line:
            first_new_line = False
            continue

        html = f"""
            <style>
                @keyframes shrinkSpace {{
                    0%   {{ height: calc(17px * 1.4); opacity: 1; }}
                    100% {{ height: 0; opacity: 0; }}
                }}
                .trans-box {{
                    max-width: 90%;
                    margin: auto;
                    padding: 10px;
                    color: black;
                    font-size: 17px;
                    line-height: 1.4;
                    text-align: center;
                }}
                .space-line {{
                    height: calc(17px * 1.4);
                    animation: shrinkSpace 0.3s ease-out forwards;
                }}
            </style>

            <div class="trans-box">
                <div class="space-line"></div>
                <div style="display:block;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{" ".join(prev_subt)}</span></div>
                <div style="display:block;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{" ".join(subt)}</span></div>
            </div>
        """
        text_area.markdown(html, unsafe_allow_html=True)
        time.sleep(0.3)

    else:
        html = f"""
            <div style="
                max-width: 90%;
                margin: auto;
                padding: 10px;
                color: black;
                font-size: 17px;
                line-height: 1.4;
                text-align: center;
            ">
                <div style="display:block;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{" ".join(prev_subt)}</span></div>
                <div style="display:block;"><span style="display:inline-block; background:rgba(0,0,0,0.1); padding:4px 10px; border-radius:8px;">{" ".join(subt)}</span></div>
            </div>
        """
        text_area.markdown(html, unsafe_allow_html=True)
        time.sleep(0.05)