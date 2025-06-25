import os
import logging
import fasttext
from google import genai
from google.genai import types

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
