import os, time
from tqdm import tqdm
import numpy as np

import matplotlib.pyplot as plt
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

# === CONFIG ===
PROJECT_ID = "formal-wonder-477401-g4"
API_ENDPOINT = "us-central1-speech.googleapis.com"
AUDIO_PATH = "translation_googleapi/audios/audio4_mono.wav"
MODEL = "chirp_3"

# === INIT CLIENT ===
client = SpeechClient(client_options=ClientOptions(api_endpoint=API_ENDPOINT))
with open(AUDIO_PATH, "rb") as f:
    content = f.read()

config = cloud_speech.RecognitionConfig(
    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
    language_codes=["ko-KR"],
    model=MODEL,
)

req = cloud_speech.RecognizeRequest(
    recognizer=f"projects/{PROJECT_ID}/locations/us-central1/recognizers/_",
    config=config,
    content=content,
)

_ = client.recognize(request=req)