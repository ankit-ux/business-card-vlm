import json
import os
import re

import requests

from app.services.image import to_base64_data_url

VLM_PROVIDER = os.getenv("VLM_PROVIDER", "dashscope").lower()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-vl-plus")
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "Qwen/Qwen2.5-VL-3B-Instruct")

PROMPT = """You are a data-extraction engine. Look at this business card image and
extract the following fields exactly:
- first_name
- last_name
- position (job title)
- company
- location (city/state/country as printed, or address)
- phone (primary phone number as printed)
- email

Rules:
- Return ONLY a single valid JSON object, nothing else. No markdown, no code fences, no commentary.
- If a field is not present on the card, use an empty string "" for it.
- Do not invent information that is not on the card.

Example output:
{"first_name": "Jane", "last_name": "Doe", "position": "Sales Manager", "company": "Acme Corp", "location": "Austin, TX", "phone": "+1 512-555-0100", "email": "jane.doe@acme.com"}
"""

FIELDS = ["first_name", "last_name", "position", "company", "location", "phone", "email"]

_local_model = None
_local_processor = None


class VLMError(Exception):
    pass


def extract_lead_fields(image_bytes: bytes) -> dict:
    if VLM_PROVIDER == "local":
        raw_text = _extract_local(image_bytes)
    else:
        raw_text = _extract_dashscope(image_bytes)
    return _parse_json_response(raw_text)


def _extract_dashscope(image_bytes: bytes) -> str:
    if not DASHSCOPE_API_KEY:
        raise VLMError("DASHSCOPE_API_KEY is not set. Add it to your .env file.")

    data_url = to_base64_data_url(image_bytes)
    payload = {
        "model": DASHSCOPE_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(DASHSCOPE_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise VLMError(f"DashScope API error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise VLMError(f"Unexpected DashScope response shape: {data}") from e


def _extract_local(image_bytes: bytes) -> str:
    """Runs Qwen2.5-VL locally via transformers. Requires requirements-local.txt
    and, in practice, a GPU. Model is loaded once and cached in-process."""
    global _local_model, _local_processor
    import io

    from PIL import Image

    if _local_model is None:
        try:
            import torch
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
        except ImportError as e:
            raise VLMError(
                "Local VLM mode requires extra packages. "
                "Run: pip install -r requirements-local.txt"
            ) from e

        _local_processor = AutoProcessor.from_pretrained(LOCAL_MODEL_NAME)
        _local_model = Qwen2VLForConditionalGeneration.from_pretrained(
            LOCAL_MODEL_NAME,
            torch_dtype="auto",
            device_map="auto",
        )

    import torch

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": PROMPT},
            ],
        }
    ]
    text = _local_processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _local_processor(text=[text], images=[image], return_tensors="pt")
    inputs = {k: v.to(_local_model.device) for k, v in inputs.items()}

    with torch.no_grad():
        generated_ids = _local_model.generate(**inputs, max_new_tokens=512)

    trimmed = generated_ids[:, inputs["input_ids"].shape[1]:]
    output_text = _local_processor.batch_decode(
        trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_text[0] if output_text else ""


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise VLMError(f"Model did not return parseable JSON: {text[:300]}")
        obj = json.loads(match.group(0))

    return {field: str(obj.get(field, "") or "").strip() for field in FIELDS}
