import threading
import time

from google.cloud import speech
#from google.cloud import translate_v3

from microphone_stream import CHUNK, RATE, MicrophoneStream


PROJECT_ID = "formal-wonder-477401-g4"


class ThreadManager:
    def __init__(self, lang_audio, lang_subt):
        self.transc_client = speech.SpeechClient()
        #self.transl_client = translate_v3.TranslationServiceClient()

        self.thread_stt = threading.Thread(target=self.speech_to_text, daemon=True)
        #self.thread_transl = threading.Thread(target=self.translate, daemon=True)
        self.output_stt, self.output_transl = "", ""
        self.prev_input_transl = ""

        self.lang_audio = lang_audio
        self.lang_subt = lang_subt
    
    @property
    def streaming_config(self):
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=self.lang_audio,
            enable_word_time_offsets=True,
        )

        return speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )

    def speech_to_text(self):
        with MicrophoneStream(RATE, CHUNK) as stream:
            audio_generator = stream.generator()
            requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in audio_generator
            )
            responses = self.transc_client.streaming_recognize(self.streaming_config, requests)
            for response in responses:
                if not response.results:
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                self.output_stt = result.alternatives[0].transcript

    """def translate(self):
        while True:
            # check if the transcription changed
            if self.output_stt and self.output_stt != self.prev_input_transl:
                self.prev_input_transl = self.output_stt

                response = self.transl_client.translate_text(
                    contents=[self.output_stt],
                    target_language_code="fr",
                    parent=f"projects/{PROJECT_ID}/locations/global"
                )

                self.output_transl = response.translations[0].translated_text

            time.sleep(0.05)"""
    
    def start(self):
        self.thread_stt.start()
        #self.thread_transl.start()