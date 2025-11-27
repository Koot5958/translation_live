import torch
from transformers import pipeline, M2M100Tokenizer, M2M100ForConditionalGeneration

from utils.parameters import SR


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "facebook/m2m100_418M"
model = M2M100ForConditionalGeneration.from_pretrained(model_name).to(DEVICE)
model.eval()
model.half()

asr, tokenizer = None, None


def load_models(lang_src):
    global asr
    global tokenizer

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
    tokenizer = M2M100Tokenizer.from_pretrained(model_name)
    tokenizer.src_lang = lang_src


def transcribe(segment, start, end):

    if len(segment) < SR//10 or end <= start:
        return "..."

    with torch.no_grad():
        result = asr(segment)

        chunks = result["chunks"]

        cropped = [c for c in chunks if c["timestamp"][0] >= start and end >= c["timestamp"][0]]
        cropped_text = " ".join(c["text"].strip() for c in cropped).strip()

        # -- logs -- #
        print(
            "\n--- OCR LOG -------------------------\n"
            f"  Result: {result['text']}\n"
            f"  Cropped: {cropped_text}\n"
            "-------------------------------------\n"
        )
        
        del result
        del chunks
        del cropped
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return cropped_text


def translate(text, lang_target):
    if len(text) < 4:
        return "..."

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