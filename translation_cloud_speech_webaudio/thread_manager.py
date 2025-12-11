import threading
import time

import streamlit as st
from google.cloud import speech
from google.cloud import translate_v3

from utils.parameters import THREAD_NAMES, REFRESH_TRANSLATE_RATE, SR
from utils.logs import print_logs


PROJECT_ID = "formal-wonder-477401-g4"
TIME_BETWEEN_SENTENCES = 4


class ThreadManager:
    def __init__(self, lang_audio, lang_transl, audio_processor):
        self.transc_client = speech.SpeechClient()
        self.transl_client = translate_v3.TranslationServiceClient()

        self.thread_stt = threading.Thread(target=self.speech_to_text, args=(audio_processor,), name=THREAD_NAMES[0])
        self.thread_transl = threading.Thread(target=self.translate, name=THREAD_NAMES[1])
        self.output_stt, self.output_transl = "", ""
        self.prev_output_stt = []
        self.prev_input_transl = ""

        self.prev_transc = [[None, None]]
        self.prev_transcs = []

        self.lang_audio = lang_audio
        self.lang_transl = lang_transl

        self.running = True
        self.last_transc_time = time.time()

        self.add_to_stt_output = ""

    @property
    def streaming_config(self):
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SR,
            language_code=self.lang_audio,
            enable_word_time_offsets=True,
            profanity_filter=True,
        )

        return speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )

    def speech_to_text(self, audio_processor):
        audio_generator = audio_processor.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )
        responses = self.transc_client.streaming_recognize(self.streaming_config, requests)
        for response in responses:
            if not self.running:
                break

            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            if time.time() - self.last_transc_time > TIME_BETWEEN_SENTENCES:
                self.add_to_stt_output = ""
            self.last_transc_time = time.time()

            output = result.alternatives[0].transcript

            # more stability in the output to avoid changes far away in the transcription
            output_split = output.split(" ")
            if len(self.prev_output_stt) > len(output_split):
                output_split = self.prev_output_stt
            elif len(self.prev_output_stt) > 3:
                output_split = self.prev_output_stt[:-3] + output_split[len(self.prev_output_stt)-3:]
            output = " ".join(output_split)
            self.prev_output_stt = output_split

            if result.is_final:
                # potentially add the previous transcript outputs (usefull when final transcripts are computed too fast)
                self.prev_transcs.append([output, time.time()])
                for transc in self.prev_transcs:
                    if time.time() - transc[1] > TIME_BETWEEN_SENTENCES:
                        self.prev_transcs.remove(transc)
                self.add_to_stt_output = " ".join([transc for transc, _ in self.prev_transcs])

                # clear previous inter output
                self.prev_output_stt = []
            else:
                self.prev_transc = [result.alternatives[0].transcript, time.time()]

            self.output_stt = self.add_to_stt_output + output

    def translate(self):
        while self.running:
            # check if the transcription changed
            if self.output_stt and self.output_stt != self.prev_input_transl:
                self.prev_input_transl = self.output_stt

                response = self.transl_client.translate_text(
                    contents=[self.output_stt],
                    target_language_code=self.lang_transl,
                    source_language_code=self.lang_audio,
                    parent=f"projects/{PROJECT_ID}/locations/global"
                )

                self.output_transl = response.translations[0].translated_text

            time.sleep(REFRESH_TRANSLATE_RATE)
    
    def start(self):
        if not self.thread_stt.is_alive():
            self.thread_stt.start()
        if not self.thread_transl.is_alive():
            self.thread_transl.start()

    def stop(self):
        self.running = False
        if hasattr(self, "stream") and self.stream is not None:
            self.stream.close()
    

def stop_all_threads():
    # stop threads
    if "threads" in st.session_state:

        print_logs("Stopping threads...", log_type="threads")
        st.session_state.threads.stop()

        # wait for speech/translation threads to finish
        for t in threading.enumerate():
            if any(prefix in t.name for prefix in THREAD_NAMES):
                t.join(timeout=2)

        del st.session_state["threads"]