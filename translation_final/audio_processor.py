import numpy as np
import threading
from collections import deque

from streamlit_webrtc import AudioProcessorBase
from scipy.signal import resample_poly

from utils.parameters import SR


class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.buffer = deque()
        self.lock = threading.Lock()
        self.sr = SR
        self.max_samples = self.sr * 4
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
    
    """async def recv_queued(self, frames):
        if not frames:
            return frames
        
        chunks = []
        for frame in frames:
            arr = frame.to_ndarray()
            audio_float = self._to_float32(arr)
            audio_mono = self._to_mono(audio_float, frame).astype(np.float32)
            audio_mono_16k = resample_poly(audio_mono, up=self.sr, down=frame.sample_rate)
            chunks.append(audio_mono_16k)

        if chunks:
            segment = np.concatenate(chunks)
            self.fill_buffer(segment)

        return frames"""

    def fill_buffer(self, audio):
        with self.lock:
            self.buffer.append(audio)
            total_samples = sum(arr.size for arr in self.buffer)
            while total_samples > self.max_samples and len(self.buffer) > 0:
                removed = self.buffer.popleft()
                total_samples -= removed.size

    def pop_buffer(self, clear=True, db_threshold=-35):
        with self.lock:
            if not self.buffer:
                return np.zeros(0, dtype=np.float32)
            arr = np.concatenate(list(self.buffer)).astype(np.float32)
            if clear:
                self.buffer.clear()

        print(level_from_buffer(arr))
        if level_from_buffer(arr) < db_threshold:
            return np.zeros(0, dtype=np.float32)
        return arr

    def stop(self):
        self.running = False


def level_from_buffer(buffer, window_s=2):
    win_size = window_s * SR
    if win_size <= 0 or win_size > len(buffer):
        win_size = len(buffer)

    max_db = -200
    for i in range(0, len(buffer) - win_size + 1, win_size // 2):
        win = buffer[i:i + win_size]
        sq_mean = np.nanmean(win ** 2)
        if sq_mean <= 0 or np.isnan(sq_mean):
            continue

        rms = np.sqrt(sq_mean)
        db = 20 * np.log10(rms + 1e-6)

        if db > max_db:
            max_db = db

    return max_db


def normalize_buffer(buffer, target_mean=0.1):
    rms = np.sqrt(np.mean(buffer**2))
    return buffer * (target_mean / (rms + 1e-9))