import os

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

PROJECT_ID = os.getenv("PROJECT_ID")


def transcribe_chirp(
    audio_file: str,
) -> cloud_speech.RecognizeResponse:
    """Transcribes an audio file using the Chirp model of Google Cloud Speech-to-Text API.
    Args:
        audio_file (str): Path to the local audio file to be transcribed.
            Example: "resources/audio.wav"
    Returns:
        cloud_speech.RecognizeResponse: The response from the Speech-to-Text API containing
        the transcription results.

    """
    # Instantiates a client
    client = SpeechClient(
        client_options=ClientOptions(
            api_endpoint="asia-southeast1-speech.googleapis.com",
        )
    )

    # Reads a file as bytes
    with open(audio_file, "rb") as f:
        audio_content = f.read()

    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=["fr-FR"],
        model="chirp",
    )

    for i in range(2):
        request = cloud_speech.RecognizeRequest(
            recognizer=f"projects/{PROJECT_ID}/locations/asia-southeast1/recognizers/_",
            config=config,
            content=audio_content,
        )

        # Transcribes the audio into text
        response = client.recognize(request=request)

        for result in response.results:
            print(f"Transcript: {result.alternatives[0].transcript}")

    return response

if __name__ == '__main__':
    transcribe_chirp('translation_googleapi/audios/audio2.mp3')