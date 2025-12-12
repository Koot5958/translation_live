import numpy as np
import queue

from streamlit_webrtc import AudioProcessorBase
from scipy.signal import resample_poly

from utils.parameters import SR, CHUNK


class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.buffer = queue.Queue()
        self._temp_buffer = []
        self.running = True
        self.inter_process = False

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
        audio_mono_16k = resample_poly(audio_mono, up=SR, down=frames.sample_rate)
        self.fill_buffer(audio_mono_16k)
        return frames

    def fill_buffer(self, audio):
        audio_int16 = (audio * 32767).astype(np.int16)
        self._temp_buffer.extend(audio_int16) 

        if len(self._temp_buffer) >= CHUNK:
            # conversion en octets car c'est attendu par l'API
            segment_np = np.array(self._temp_buffer, dtype=np.int16)
            audio_bytes = segment_np.tobytes()

            self.buffer.put(audio_bytes)
            self._temp_buffer = []

    def generator(self):
        while self.running and not self.inter_process:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self.buffer.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self.buffer.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)

    def stop(self):
        if self.running:
            self.running = False
            self.buffer.put(None)