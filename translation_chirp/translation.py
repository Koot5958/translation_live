import time

import numpy as np

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions

from utils.parameters import SR


PROJECT_ID = "formal-wonder-477401-g4"
REGION = "asia-southeast1"
API_ENDPOINT = f"{REGION}-speech.googleapis.com"
RECOGNIZER = f"projects/{PROJECT_ID}/locations/{REGION}/recognizers/_"
MODEL = "chirp_3"


def google_audio_generator(ctx):
    audio_proc = ctx.audio_processor

    # Chunk initial silence pour lancer le stream
    silence = np.zeros(int(SR * 0.2), dtype=np.float32)
    pcm16 = (np.clip(silence, -1, 1) * 32767).astype(np.int16).tobytes()
    print(pcm16)
    yield cloud_speech.StreamingRecognizeRequest(audio=pcm16)
    print("test13")

    while True:
        chunk = audio_proc.pop_buffer(clear=True, db_threshold=-100)
        if chunk is None:
            dummy = np.zeros(int(SR * 0.05), dtype=np.float32)  # 50ms
            pcm16 = (np.clip(dummy, -1, 1) * 32767).astype(np.int16).tobytes()
            yield cloud_speech.StreamingRecognizeRequest(audio=pcm16)
            time.sleep(0.02)
            continue

        print("chunk shape:", chunk.shape, "dtype:", chunk.dtype)
        pcm16 = (np.clip(chunk, -1, 1) * 32767).astype(np.int16).tobytes()
        print(pcm16)
        yield cloud_speech.StreamingRecognizeRequest(audio=pcm16)


def google_streaming_stt(ctx, lang='fr-FR'):
    """Streaming transcription from Streamlit microphone to Google Chirp."""
    client = SpeechClient(
        client_options=ClientOptions(
            api_endpoint=f"{REGION}-speech.googleapis.com"
        )
    )

    recognition_config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=[lang],
        model="chirp_3",
    )

    streaming_config = cloud_speech.StreamingRecognitionConfig(
        config=recognition_config,
    )

    config_request = cloud_speech.StreamingRecognizeRequest(
        recognizer=f"projects/{PROJECT_ID}/locations/{REGION}/recognizers/_",
        streaming_config=streaming_config,
    )

    def request_generator():
        yield config_request
        yield from google_audio_generator(ctx)

    responses = client.streaming_recognize(requests=request_generator())

    print("t0")
    for response in responses:
        print("t1")
        for result in response.results:
            print("test")
            print(result.alternatives[0])
            yield result.alternatives[0].transcript
