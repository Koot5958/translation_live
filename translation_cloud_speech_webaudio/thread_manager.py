import threading
import time

import streamlit as st
from google.cloud import speech
from google.cloud import translate_v3

from utils.parameters import THREAD_NAMES, REFRESH_TRANSLATE_RATE, SR, STABILITY_MARGIN, TIME_BETWEEN_SENTENCES, STREAMING_LIMIT
from utils.logs import print_logs
from utils.display import split_text, join_text


PROJECT_ID = "formal-wonder-477401-g4"


class ThreadManager:
    def __init__(self, lang_audio, lang_transl, audio_processor):
        self.transc_client = speech.SpeechClient()
        self.transl_client = translate_v3.TranslationServiceClient()

        self.audio_processor = audio_processor

        self.thread_stt = threading.Thread(target=self.speech_to_text, name=THREAD_NAMES[0])
        self.thread_transl = threading.Thread(target=self.translate, name=THREAD_NAMES[1])

        self.output_stt, self.output_transl = [], []
        self.prev_output_stt, self.prev_output_transl = [], []
        self.prev_input_transl = []

        self.latest_final_transcs = []
        self.prefix_stt_output = []

        self.lang_audio, self.lang_transl = lang_audio, lang_transl

        self.last_transc_time = time.time()
        self.start_time = time.time()
        self.running = True

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

    def speech_to_text(self):
        while self.running:
            self.start_time = time.time()
            print_logs("Start STT process...")

            self.audio_processor.inter_process = False
            generator = self.audio_processor.generator()
            requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in generator
            )
            responses = self.transc_client.streaming_recognize(self.streaming_config, requests)

            for response in responses:
                if not self.running or (time.time() - self.start_time) > STREAMING_LIMIT:
                    print_logs("Stop STT process...")
                    self.audio_processor.inter_process = True
                    break

                if not response.results or not (result := response.results[0]).alternatives:
                    continue

                # If nobody talks and then the conversation start again -> clear previous subtitles
                if time.time() - self.last_transc_time > TIME_BETWEEN_SENTENCES:
                    self.prefix_stt_output = []
                self.last_transc_time = time.time()

                output_raw = result.alternatives[0].transcript
                output = split_text(output_raw, self.lang_audio)

                # stabilize the beginning of the output sentences to avoid changes of words that are too far
                if len(self.prev_output_stt) > len(output):
                    output = self.prev_output_stt
                elif len(self.prev_output_stt) > STABILITY_MARGIN:
                    output = self.prev_output_stt[:-STABILITY_MARGIN] + output[len(self.prev_output_stt)-STABILITY_MARGIN:]

                # add a prefix to the intermediate output (useful in case final transcripts arrived too fast)
                if result.is_final:
                    self.latest_final_transcs.append([output, time.time()])
                    self.latest_final_transcs = [
                        transc_data for transc_data in self.latest_final_transcs
                        if time.time() - transc_data[1] <= TIME_BETWEEN_SENTENCES
                    ]
                    self.prefix_stt_output = [w for transc,_ in self.latest_final_transcs for w in transc]

                self.output_stt = self.prefix_stt_output + output
                self.prev_output_stt = [] if result.is_final else output

    def translate(self):
        while self.running:
            # check if the transcription has changed
            if self.output_stt and self.output_stt != self.prev_input_transl:
                self.prev_input_transl = self.output_stt
                input_transl = join_text(self.output_stt, self.lang_audio)

                response = self.transl_client.translate_text(
                    contents=[input_transl],
                    target_language_code=self.lang_transl,
                    source_language_code=self.lang_audio,
                    parent=f"projects/{PROJECT_ID}/locations/global"
                )

                output_raw = response.translations[0].translated_text
                output = split_text(output_raw, self.lang_transl)

                # stabilize the beginning of the output sentences to avoid changes of words that are too far
                if len(self.prev_output_transl) > len(output):
                    output = self.prev_output_transl
                elif len(self.prev_output_transl) > STABILITY_MARGIN:
                    output = self.prev_output_transl[:-STABILITY_MARGIN] + output[len(self.prev_output_transl)-STABILITY_MARGIN:]

                self.output_transl = output
                self.prev_output_transl = output

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