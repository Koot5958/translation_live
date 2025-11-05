import numpy as np

import torch
import librosa
from transformers import pipeline, M2M100Tokenizer, M2M100ForConditionalGeneration


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

model_name = "facebook/m2m100_418M"
model = M2M100ForConditionalGeneration.from_pretrained(model_name).to(DEVICE)

asr, tokenizer = None, None


def load_models(lang_src):
    global asr
    global tokenizer

    asr = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-medium",
        device=0 if torch.cuda.is_available() else -1,
        dtype=torch.float16 if torch.cuda.is_available() else None,
        return_timestamps="word",
        language=lang_src,
    )
    tokenizer = M2M100Tokenizer.from_pretrained(model_name)
    tokenizer.src_lang = lang_src


class PreProcessed:
    def __init__(self, file):
        self.file, self.sr = librosa.load(file, sr=16000, mono=True)

    @property
    def raw_data(self):
        return self.file.astype(np.float32)
    
    def norm_data(self, start, end):
        data = self.raw_data[int(start * self.sr) : int(end * self.sr)]

        target_rms = 0.1
        rms = np.sqrt(np.mean(data**2))
        return data * (target_rms / (rms + 1e-9))


def transcribe(segment, real_overlap):
    with torch.no_grad():
        result = asr(segment)

        chunks = result["chunks"]

        cropped = [c for c in chunks if c["timestamp"][0] >= real_overlap]
        cropped_text = " ".join(c["text"].strip() for c in cropped).strip()
        
        return cropped_text


def translate(text, lang_target):
    if len(text) < 4:
        return ""

    inputs = tokenizer(text, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.get_lang_id(lang_target),
            max_length=256,
            num_beams=5,
            no_repeat_ngram_size=3,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
