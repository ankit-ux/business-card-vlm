import base64
import io
import os

from fastapi import HTTPException, UploadFile
from PIL import Image

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "10"))
MAX_DIMENSION = 1600  # longest side, after resize (keeps VLM prompt small/fast)


def validate_image(file: UploadFile, content: bytes) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}' for {file.filename}. "
            f"Allowed: jpg, png, webp.",
        )
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_IMAGE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename} is {size_mb:.1f}MB, exceeds the {MAX_IMAGE_MB}MB limit.",
        )
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail=f"{file.filename} is not a valid image.")


def preprocess_image(content: bytes) -> bytes:
    """Re-encode to RGB JPEG, downscale if very large, to keep VLM calls fast/cheap."""
    img = Image.open(io.BytesIO(content))
    img = img.convert("RGB")

    w, h = img.size
    longest = max(w, h)
    if longest > MAX_DIMENSION:
        scale = MAX_DIMENSION / longest
        img = img.resize((int(w * scale), int(h * scale)))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


def to_base64_data_url(content: bytes) -> str:
    b64 = base64.b64encode(content).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"
