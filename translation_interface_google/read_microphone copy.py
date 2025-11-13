import time
import numpy as np

import threading
from collections import deque

import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
from scipy.signal import resample_poly
from translation_temp import load_models, transcribe, translate, model


class AudioProcessor(AudioProcessorBase):
    def __init__(self, sr=16000):
        self.buffer = deque()
        self.lock = threading.Lock()
        self.sr = sr
        self.max_samples = self.sr * 2
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
        audio_mono_16k = resample_poly(audio_mono, up=self.sr, down=frames.sample_rate)
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

st.set_page_config(layout="centered")
st.title("Audio capture in real time")
placeholder = st.empty()

if model is None:
    load_models('fr')

ctx = webrtc_streamer(
    key="audio-level",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if ctx and ctx.audio_processor:
    while ctx.state.playing:
        buffer = ctx.audio_processor.pop_buffer()

        #------ Audio level ------#
        #sq_mean = np.nanmean(buffer**2)
        #if not np.isnan(sq_mean):
        #    rms = np.sqrt(sq_mean)

        #    db = 20 * np.log10(rms + 1e-6)
        #    db = np.clip(db, -60, 0)
        #    bar_len = int((db + 60) / 60 * 50)

        #    audio_level = "█" * bar_len + " " * (50 - bar_len)
        #    placeholder.write(f"Audio level: {audio_level}")
        
        #------ Transcription and translation ------#
        if len(buffer) != 0:
            placeholder.write(f"Audio transcript: {transcribe(buffer, 0)}")

        time.sleep(4)
