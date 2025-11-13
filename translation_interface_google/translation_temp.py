import time
import os

import numpy as np

import torch
import librosa
from transformers import pipeline, M2M100Tokenizer, M2M100ForConditionalGeneration


asr, model, tokenizer = None, None, None


def load_models(lang_src):
    global asr
    global tokenizer
    global model

    # transcription
    asr = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-medium",
        device=0 if torch.cuda.is_available() else -1,
        dtype=torch.float16 if torch.cuda.is_available() else None,
        return_timestamps="word",
        language=lang_src,
    )

    # translation
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    model_name = "facebook/m2m100_418M"
    tokenizer = M2M100Tokenizer.from_pretrained(model_name)
    model = M2M100ForConditionalGeneration.from_pretrained(model_name).to(DEVICE)
    tokenizer.src_lang = lang_src


class PreProcessed:
    def __init__(self, file):
        self.file, self.sr = librosa.load(file, sr=16000, mono=True)

    @property
    def raw_data(self):
        return self.file.astype(np.float32)
    
    def norm_data(self, start, end, all=False):
        data = self.raw_data if all else self.raw_data[int(start * self.sr) : int(end * self.sr)]

        target_rms = 0.1
        rms = np.sqrt(np.mean(data**2))
        return data * (target_rms / (rms + 1e-9))


def transcribe(segment, real_overlap):
    with torch.no_grad():
        result = asr(segment)

        chunks = result["chunks"]

        cropped = [c for c in chunks if c["timestamp"][0] >= real_overlap]
        cropped_text = " ".join(c["text"].strip() for c in cropped).strip()
        
        del result
        del chunks
        del cropped
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return cropped_text


def translate(text, lang_target):
    if len(text) < 4:
        return ""

    inputs = tokenizer(text, return_tensors="pt")#.to(DEVICE)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.get_lang_id(lang_target),
            max_length=256,
            num_beams=5,
            no_repeat_ngram_size=3,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def _example():
    import matplotlib.pyplot as plt
    from tqdm import tqdm


    load_models('fr')
    main_color = "#1845a5"

    all_times = [] 
    for j in range(8):
        preprocessed = PreProcessed('translation_interface/audios/audio2_mono.wav')

        times = []
        for i in tqdm(range(50)):
            start = time.time()
            segment = preprocessed.norm_data(0, 6)
            transc = transcribe(segment, 0)
            times.append(time.time() - start)
            torch.cuda.empty_cache()
        all_times.append(times)

    plt.style.use('fivethirtyeight')
    plt.figure(figsize=(9, 6))

    for times in all_times:
        plt.plot(
            range(1, len(times)+1),
            times,
            color=main_color,
            linewidth=1,
            alpha=0.3,     # forte transparence
        )
    
    mean_times = np.mean(np.array(all_times), axis=0)

    # Tracer la courbe moyenne par-dessus (pleine opacité)
    plt.plot(
        range(1, len(mean_times)+1),
        mean_times,
        color=main_color,
        linewidth=2,
        label="Mean",
    )

    plt.xlabel('Segment number', fontsize=12)
    plt.ylabel('Execution time (s)', fontsize=12)
    plt.title('Recognize() execution times', fontsize=14, fontweight='bold')
    plt.legend(fontsize=11)
    plt.grid(alpha=0.3)
    plt.tight_layout()

    os.makedirs('translation_interface/plots', exist_ok=True)
    plt.savefig('translation_interface/plots/recognize_execution_times.png', dpi=300)
    plt.close()
