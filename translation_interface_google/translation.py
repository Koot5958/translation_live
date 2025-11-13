import queue
import threading
import time

import numpy as np

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from read_microphone import AudioProcessor


PROJECT_ID = "formal-wonder-477401-g4"
LOCATION = "asia-southeast1"
API_ENDPOINT = f"{LOCATION}-speech.googleapis.com"
RECOGNIZER = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/_"
MODEL = "chirp_3"
SR = 16000
CHUNK_MAX_BYTES = 12000


def transcribe_streaming_v2(audio_proc, out_queue):
    """Transcribes audio from a live AudioProcessor buffer using Google Cloud Speech-to-Text V2."""
    
    client = SpeechClient(client_options=ClientOptions(api_endpoint=API_ENDPOINT))

    config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SR,
            audio_channel_count=1,
        ),
        language_codes=["fr-FR"],
        model=MODEL,
    )
    streaming_config = cloud_speech.StreamingRecognitionConfig(config=config)

    config_request = cloud_speech.StreamingRecognizeRequest(
        recognizer=f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/_",
        streaming_config=streaming_config,
    )

    def request_generator():
        yield config_request

        while audio_proc.running:
            buf = audio_proc.pop_buffer(clear=True)
            if buf.size == 0:
                time.sleep(0.02)
                continue
            
            # float32 [-1,1] -> PCM16
            clipped = np.clip(buf, -1.0, 1.0)
            pcm16 = (clipped * 32767.0).astype(np.int16).tobytes()

            # chunker < 24kB
            start = 0
            while start < len(pcm16):
                end = min(start + CHUNK_MAX_BYTES, len(pcm16))
                yield cloud_speech.StreamingRecognizeRequest(audio=pcm16[start:end])
                start = end

            time.sleep(0.02)

    # appel streaming_recognize
    print("t10")
    responses_iterator = client.streaming_recognize(requests=request_generator())
    responses = []
    print("t3")
    for response in responses_iterator:
        print("t4")
        responses.append(response)
        for result in response.results:
            out_queue.put(result.alternatives[0].transcript)
            print(f"Transcript: {result.alternatives[0].transcript}")

    return responses


if __name__ == '__main__':
    ctx = webrtc_streamer(
        key="audio-level",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
    )

    st_transcript = st.empty()
    transcript_q = queue.Queue()
    worker_thread = None

    if ctx and ctx.audio_processor:
        audio_proc: AudioProcessor = ctx.audio_processor

        if worker_thread is None:
            worker_thread = threading.Thread(target=transcribe_streaming_v2, args=(audio_proc, transcript_q), daemon=True)
            worker_thread.start()

        while ctx.state.playing:
            while not transcript_q.empty():
                print("t7")
                item = transcript_q.get()
                print(f'item: {item}')
                st_transcript.write(item)
            time.sleep(0.1)

        # audio_proc.stop()