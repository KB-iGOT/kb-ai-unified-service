# Language detection for English/Indic (service function)
import pandas as pd

import os
import logging
import fasttext
from google import genai
from google.genai import types

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

# --- Transformer-based Profanity Detection (English/Indic) ---
_transformer_models = {
    'english': None,
    'indic': None
}

def _detect_language(text):
    if pd.isna(text):
        return "unknown"
    text = str(text)
    script_ranges = {
        'hindi': (0x0900, 0x097F),
        'bengali': (0x0980, 0x09FF),
        'tamil': (0x0B80, 0x0BFF),
        'telugu': (0x0C00, 0x0C7F),
        'kannada': (0x0C80, 0x0CFF),
        'malayalam': (0x0D00, 0x0D7F),
        'gujarati': (0x0A80, 0x0AFF),
        'punjabi': (0x0A00, 0x0A7F),
        'oriya': (0x0B00, 0x0B7F),
        'marathi': (0x0900, 0x097F),
    }
    char_counts = dict.fromkeys(script_ranges, 0)
    total_chars = 0
    for char in text:
        char_code = ord(char)
        total_chars += 1
        for lang, (start, end) in script_ranges.items():
            if start <= char_code <= end:
                char_counts[lang] += 1
                break
    if total_chars == 0:
        return "unknown"
    max_lang = max(char_counts, key=char_counts.get)
    if char_counts[max_lang] / total_chars > 0.3:
        return max_lang
    return "mixed/english"

def _load_english_model():
    if _transformer_models['english'] is not None:
        return _transformer_models['english']
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained("unitary/toxic-bert")
    model = AutoModelForSequenceClassification.from_pretrained("unitary/toxic-bert").to(device)
    id2label = model.config.id2label if hasattr(model.config, 'id2label') else {0: 'NOT_TOXIC', 1: 'TOXIC'}
    _transformer_models['english'] = (tokenizer, model, id2label, device)
    return _transformer_models['english']

def _load_indic_model():
    if _transformer_models['indic'] is not None:
        return _transformer_models['indic']
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_name = "Hate-speech-CNERG/indic-abusive-allInOne-MuRIL"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device)
    _transformer_models['indic'] = (tokenizer, model, device)
    return _transformer_models['indic']

def check_profanity_transformer(text: str):
    """
    Detect profanity using transformer models (English/Indic).
    Returns: dict with status, message, responseData
    """
    logger.info(f"Checking profanity (transformer) for: {text}")
    if pd.isna(text) or str(text).strip() == "":
        return {
            "status": "error",
            "message": "Input text is empty",
            "responseData": None
        }
    lang = _detect_language(text)
    logger.info(f"Detected language: {lang}")
    try:
        if lang in ["mixed/english", "english"]:
            tokenizer, model, id2label, device = _load_english_model()
            inputs = tokenizer(str(text), return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                logits = model(**inputs).logits
            probs = torch.sigmoid(logits).cpu().numpy()[0]
            toxic_indices = [i for i, p in enumerate(probs) if p >= 0.4]
            toxic_labels = [id2label[i] for i in toxic_indices]
            toxic_confidences = [float(probs[i]) for i in toxic_indices]
            max_conf = float(max(probs)) if len(probs) > 0 else 0.0
            toxic_labels_str = ','.join(toxic_labels) if toxic_labels else None
            if toxic_labels:
                main_label = 'Profane'
                main_confidence = max(toxic_confidences)
            else:
                main_label = 'Non-Profane'
                main_confidence = 1.0 - max_conf
            if main_label == 'Profane' and max_conf < 0.8:
                main_label = 'Non-Profane'
                main_confidence = 1.0 - max_conf
            if main_label == 'Non-Profane' and main_confidence < 0.8:
                main_label = 'Profane'
                main_confidence = 1.0 - main_confidence
            return {
                "status": "success",
                "message": "Profanity check completed (transformer)",
                "responseData": {
                    "word": text,
                    "isProfane": main_label == 'Profane',
                    "confidence": round(main_confidence*100, 2),
                    "category": main_label,
                    "detected_language": lang,
                    "toxic_labels": toxic_labels_str
                }
            }
        else:
            tokenizer, model, device = _load_indic_model()
            encoding = tokenizer.encode_plus(
                str(text),
                add_special_tokens=True,
                max_length=512,
                padding="max_length",
                truncation=True,
                return_tensors="pt"
            )
            input_ids = encoding["input_ids"].to(device)
            attention_mask = encoding["attention_mask"].to(device)
            with torch.no_grad():
                outputs = model(input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)
                predicted_class = torch.argmax(logits, dim=1)
                confidence = torch.max(probabilities, dim=1)[0]
            pred = predicted_class.cpu().item()
            conf = confidence.cpu().item()
            if pred == 0:
                label = 'Clean'
            elif pred == 1:
                label = 'Profane/Abusive'
            else:
                label = 'Processing Error'
            return {
                "status": "success",
                "message": "Profanity check completed (transformer)",
                "responseData": {
                    "word": text,
                    "isProfane": label != 'Clean',
                    "confidence": round(conf*100, 2),
                    "category": label,
                    "detected_language": lang
                }
            }
    except Exception as e:
        logger.error(f"Transformer profanity detection error: {str(e)}")
        return {
            "status": "error",
            "message": f"Transformer model error: {str(e)}",
            "responseData": None
        }

logger = logging.getLogger("uvicorn.error")

# Load fastText model once (assume model is at app/services/profanity_model.bin or similar)
FASTTEXT_MODEL_PATH = os.environ.get(
    "FASTTEXT_PROFANITY_MODEL", "app/services/profanity_model_english.bin")
fasttext_model = None
if os.path.exists(FASTTEXT_MODEL_PATH):
    try:
        fasttext_model = fasttext.load_model(FASTTEXT_MODEL_PATH)
        logger.info(f"Loaded fastText model from {FASTTEXT_MODEL_PATH}")
    except Exception as e:
        logger.error(f"Could not load fastText model: {e}")
else:
    logger.warning(f"fastText model not found at {FASTTEXT_MODEL_PATH}")


def check_profanity_fasttext(text: str):
    logger.info(f"Checking profanity (fastText) for: {text}")
    if not fasttext_model:
        logger.error("fastText model not loaded")
        return {
            "status": "error",
            "message": "fastText model not loaded",
            "responseData": None
        }
    labels, probabilities = fasttext_model.predict(text)
    label = labels[0]
    confidence = float(probabilities[0])
    is_profane = label == "__label__offensive"
    category = "profane" if is_profane else "clean"
    logger.info(
        f"Prediction: {label}, Confidence: {confidence}, Category: {category}")
    return {
        "status": "success",
        "message": "Profanity check completed",
        "responseData": {
            "word": text,
            "isProfane": is_profane,
            "confidence": round(confidence*100, 2),
            "category": category
        }
    }


def check_profanity_llm(text: str):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "gemini-2.5-flash-preview-04-17"
    # Prepare the prompt and schema as per user logic
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"Analyze the following text for profanity and respond with a JSON object containing:\n- 'contains_profanity': boolean (true if profanity is detected, false otherwise)\n- 'confidence': number between 0-100 (confidence percentage in your assessment)\n- 'reasoning': string (brief explanation of your decision, mentioning specific words or patterns if profanity is found)\n\nText to analyze: \"{text}\"\n\nRespond only with the JSON object, no additional text.")
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["contains_profanity", "confidence", "reasoning"],
            properties={
                "contains_profanity": genai.types.Schema(
                    type=genai.types.Type.BOOLEAN,
                    description="Whether profanity was detected in the text",
                ),
                "confidence": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Confidence percentage (0-100) in the profanity assessment",
                ),
                "reasoning": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="Brief explanation of the decision, mentioning specific words or patterns if profanity is found",
                ),
            },
        ),
        system_instruction=[
            types.Part.from_text(text="""Analyze the following text for profanity also keep the context of entire sentence in mind and respond with a JSON object containing:
                - "contains_profanity": boolean (true if profanity is detected, false otherwise)
                - "confidence": number between 0-100 (confidence percentage in your assessment)
                - "reasoning": string (explanation of your decision, mentioning specific words or patterns if profanity is found and a brief explanation of your reasoning)

                Text to analyze: "{text}"

                Respond only with the JSON object, no additional text."""
                                 ),
        ],
    )
    try:
        output = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            output += chunk.text
        import json
        data = json.loads(output)
        is_profane = data.get("contains_profanity", False)
        confidence = data.get("confidence", 0)
        reasoning = data.get("reasoning", "")
        category = "profane" if is_profane else "clean"
        return {
            "status": "success",
            "message": "Profanity check completed",
            "responseData": {
                "word": text,
                "isProfane": is_profane,
                "confidence": confidence,
                "category": category,
                "reasoning": reasoning
            }
        }
    except Exception as e:
        logger.error(f"Error during LLM profanity check: {e}")
        return {
            "status": "error",
            "message": str(e),
            "responseData": None
        }
def detect_language_service(text: str, min_chars: int = 5):
    if not text or len(str(text).strip()) < min_chars:
        return {
            "status": "error",
            "message": f"Input text must be at least {min_chars} characters.",
            "detected_language": None
        }
    def _detect_language(text):
        if pd.isna(text):
            return "unknown"
        text = str(text)
        script_ranges = {
            'hindi': (0x0900, 0x097F),
            'bengali': (0x0980, 0x09FF),
            'tamil': (0x0B80, 0x0BFF),
            'telugu': (0x0C00, 0x0C7F),
            'kannada': (0x0C80, 0x0CFF),
            'malayalam': (0x0D00, 0x0D7F),
            'gujarati': (0x0A80, 0x0AFF),
            'punjabi': (0x0A00, 0x0A7F),
            'oriya': (0x0B00, 0x0B7F),
            'marathi': (0x0900, 0x097F),
        }
        char_counts = dict.fromkeys(script_ranges, 0)
        total_chars = 0
        for char in text:
            char_code = ord(char)
            total_chars += 1
            for lang, (start, end) in script_ranges.items():
                if start <= char_code <= end:
                    char_counts[lang] += 1
                    break
        if total_chars == 0:
            return "unknown"
        max_lang = max(char_counts, key=char_counts.get)
        if char_counts[max_lang] / total_chars > 0.3:
            return max_lang
        return "english"
    detected_language_raw = _detect_language(text)
    if str(detected_language_raw).lower() in ("english", "mixed/english"):
        detected_language = "english"
    else:
        detected_language = "indic"
    return {
        "status": "success",
        "detected_language": detected_language,
        "raw": detected_language_raw
    }