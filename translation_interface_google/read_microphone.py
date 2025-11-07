import time
import numpy as np

import threading
from collections import deque

import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
from scipy.signal import resample_poly


st.set_page_config(layout="centered")
st.title("Audio capture in real time")

class AudioLevelProcessor(AudioProcessorBase):
    def __init__(self, sr=16000):
        self.buffer = deque()
        self.lock = threading.Lock()
        self.sr = sr
        self.max_samples = self.sr * 0.5
    
    def _to_float32(self, data: np.ndarray) -> np.ndarray:
        if np.issubdtype(data.dtype, np.integer):
            if data.dtype == np.int16:
                return data.astype(np.float32) / 32768.0
            if data.dtype == np.int32:
                return data.astype(np.float32) / 2147483648.0
            return data.astype(np.float32)
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

    def get_audio_buffer(self, clear=True):
        with self.lock:
            if len(self.buffer) == 0:
                return np.zeros(0, dtype=np.float32)
            arr = np.concatenate(list(self.buffer)).astype(np.float32)
            if clear:
                self.buffer.clear()
        return arr

ctx = webrtc_streamer(
    key="audio-level",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioLevelProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

placeholder = st.empty()
if ctx and ctx.audio_processor:
    while ctx.state.playing:
        buffer = ctx.audio_processor.get_audio_buffer()
        placeholder.write(len(buffer))
        time.sleep(0.1)
