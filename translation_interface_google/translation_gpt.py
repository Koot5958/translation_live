import time
import threading
import queue
from collections import deque

import numpy as np
import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
from scipy.signal import resample_poly

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech


PROJECT_ID = "formal-wonder-477401-g4"
LOCATION = "asia-southeast1"
API_ENDPOINT = f"{LOCATION}-speech.googleapis.com"
RECOGNIZER = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/_"
MODEL = "chirp_3"
SR = 16000
CHUNK_MAX_BYTES = 24000


st.set_page_config(layout="centered")
st.title("Audio capture in real time")


class AudioProcessor(AudioProcessorBase):
    def __init__(self, sr=SR):
        self.buffer = deque()
        self.lock = threading.Lock()
        self.sr = sr
        self.max_samples = self.sr * 0.5
        self.running = True
    
    def _to_float32(self, data: np.ndarray) -> np.ndarray:
        if np.issubdtype(data.dtype, np.integer):
            if data.dtype == np.int16:
                return data.astype(np.float32) / 32768.0
            if data.dtype == np.int32:
                return data.astype(np.float32) / 2147483648.0
        return data.astype(np.float32)

    def _to_mono(self, data, frames) -> np.ndarray:
        if frames.layout.name == 'mono':
            return data
        if data.ndim == 2:
            axis = 0 if data.shape[0] <= 8 else 1
            return np.mean(data, axis=axis, dtype=np.float32)
        if data.ndim == 1:
            return data.reshape(-1, 2).mean(axis=1)

        return data

    def recv(self, frames):
        audio = frames.to_ndarray()
        audio_float = self._to_float32(audio[0])
        audio_mono = self._to_mono(audio_float, frames).astype(np.float32)
        audio_mono_16k = resample_poly(audio_mono, up=1, down=frames.sample_rate//self.sr)

        self.fill_buffer(audio_mono_16k)
        return frames

    def fill_buffer(self, audio):
        with self.lock:
            self.buffer.append(audio)
            total_samples = sum(arr.size for arr in self.buffer)
            while total_samples > self.max_samples and len(self.buffer) > 0:
                removed = self.buffer.popleft()
                total_samples -= removed.size

    def pop_buffer(self, clear=True):
        with self.lock:
            if not self.buffer:
                return np.zeros(0, dtype=np.float32)
            arr = np.concatenate(list(self.buffer)).astype(np.float32)
            if clear:
                self.buffer.clear()
        return arr

    def stop(self):
        self.running = False


def google_streaming_worker(audio_proc, out_queue):
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

    def request_generator():
        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=RECOGNIZER,
            streaming_config=streaming_config
        )
        yield cloud_speech.StreamingRecognizeRequest(audio=b'\0'*1600)

        # ensuite on envoie les bytes PCM16 en petits morceaux
        while audio_proc.running:
            print("test5")
            buf = audio_proc.pop_buffer(clear=True)
            if buf.size == 0:
                time.sleep(0.05)
                continue

            print("test6")
            # float32 [-1,1] -> int16 PCM
            clipped = np.clip(buf, -1.0, 1.0)
            pcm16 = (clipped * 32767.0).astype(np.int16).tobytes()

            print("sending chunk size:", len((clipped * 32767.0).astype(np.int16).tobytes()))

            # chunker < CHUNK_MAX_BYTES pour respecter la limite
            start = 0
            while start < len(pcm16):
                end = min(start + CHUNK_MAX_BYTES, len(pcm16))
                chunk = pcm16[start:end]
                yield cloud_speech.StreamingRecognizeRequest(audio=chunk)
                start = end

            time.sleep(0.01)

    print("test1")
    for resp in client.streaming_recognize(requests=request_generator()):
        print("test2")
        for r in resp.results:
            for alt in r.alternatives:
                print("test3", alt.transcript)
                text = alt.transcript
                is_final = getattr(r, "is_final", False)
                out_queue.put((is_final, text))


ctx = webrtc_streamer(
    key="audio-stt",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

placeholder = st.empty()
st_transcript = st.empty()

# thread-safe queue to receive transcripts
transcript_q = queue.Queue()

worker_thread = None

if ctx and ctx.audio_processor:
    audio_proc: AudioProcessor = ctx.audio_processor

    # start Google worker once
    if worker_thread is None:
        worker_thread = threading.Thread(target=google_streaming_worker, args=(audio_proc, transcript_q), daemon=True)
        worker_thread.start()

    # loop in main thread to display interim/final results
    while ctx.state.playing:
        while not transcript_q.empty():
            print("t2")
            item = transcript_q.get()
            is_final, text = item
            label = "Final" if is_final else "Interim"
            st_transcript.write(f"[{label}] {text}")

        time.sleep(0.1)

    # stop worker when stream stops
    audio_proc.stop()
