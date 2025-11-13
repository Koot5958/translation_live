import os
import time

from google.cloud.speech_v2 import SpeechClient
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types

PROJECT_ID = "formal-wonder-477401-g4"

def transcribe_streaming_v2(
    stream_file: str,
) -> cloud_speech_types.StreamingRecognizeResponse:
    """Transcribes audio from an audio file stream using Google Cloud Speech-to-Text API.
    Args:
        stream_file (str): Path to the local audio file to be transcribed.
            Example: "resources/audio.wav"
    Returns:
        list[cloud_speech_types.StreamingRecognizeResponse]: A list of objects.
            Each response includes the transcription results for the corresponding audio segment.
    """
    # Instantiates a client
    client = SpeechClient(
        client_options=ClientOptions(
            api_endpoint="asia-southeast1-speech.googleapis.com",
        )
    )

    # Reads a file as bytes
    with open(stream_file, "rb") as f:
        audio_content = f.read()

    # In practice, stream should be a generator yielding chunks of audio data
    chunk_length = len(audio_content) // 16
    stream = [
        audio_content[start : start + chunk_length]
        for start in range(0, len(audio_content), chunk_length)
    ]
    audio_requests = (
        cloud_speech_types.StreamingRecognizeRequest(audio=audio) for audio in stream
    )

    recognition_config = cloud_speech_types.RecognitionConfig(
        auto_decoding_config=cloud_speech_types.AutoDetectDecodingConfig(),
        language_codes=["fr-FR"],
        model="chirp_2",
    )

    streaming_config = cloud_speech_types.StreamingRecognitionConfig(
        config=recognition_config
    )

    config_request = cloud_speech_types.StreamingRecognizeRequest(
        recognizer=f"projects/{PROJECT_ID}/locations/asia-southeast1/recognizers/_",
        streaming_config=streaming_config,
    )

    def requests(config: cloud_speech_types.RecognitionConfig, audio: list):
        yield config
        yield from audio

    # Transcribes the audio into text
    start = time.time()
    responses_iterator = client.streaming_recognize(
        requests=requests(config_request, audio_requests)
    )
    print(f'duration: {time.time() - start}s')
    responses = []
    for response in responses_iterator:
        responses.append(response)
        for result in response.results:
            print(f"Transcript: {result.alternatives[0].transcript}")

    return responses


if __name__ == '__main__':
    transcribe_streaming_v2('translation_googleapi/audios/audio2_mono.wav')
