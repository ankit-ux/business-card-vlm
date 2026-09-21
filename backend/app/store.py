import os
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()

# batch_id -> {"leads": {lead_id: dict}, "order": [lead_id, ...], "files": {lead_id: path}}
BATCHES: dict[str, dict] = {}


def get_batch(batch_id: str) -> dict:
    with _lock:
        if batch_id not in BATCHES:
            BATCHES[batch_id] = {"leads": {}, "order": [], "files": {}}
        return BATCHES[batch_id]


def batch_dir(batch_id: str) -> Path:
    d = UPLOAD_DIR / batch_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def delete_batch(batch_id: str) -> None:
    import shutil

    with _lock:
        BATCHES.pop(batch_id, None)
    d = UPLOAD_DIR / batch_id
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def recompute_duplicates(batch: dict) -> None:
    """Mark is_duplicate=True on every lead after the first one that shares
    a normalized email or phone number within the batch."""
    seen_email: set[str] = set()
    seen_phone: set[str] = set()
    for lead_id in batch["order"]:
        lead = batch["leads"][lead_id]
        if lead["status"] != "success":
            lead["is_duplicate"] = False
            continue
        email = (lead.get("email") or "").strip().lower()
        phone_digits = "".join(ch for ch in (lead.get("phone") or "") if ch.isdigit())

        is_dup = False
        if email and email in seen_email:
            is_dup = True
        if phone_digits and len(phone_digits) >= 6 and phone_digits in seen_phone:
            is_dup = True

        lead["is_duplicate"] = is_dup

        if email:
            seen_email.add(email)
        if phone_digits and len(phone_digits) >= 6:
            seen_phone.add(phone_digits)


def compute_stats(batch: dict) -> dict:
    leads = [batch["leads"][lid] for lid in batch["order"]]
    total = len(leads)
    success = sum(1 for l in leads if l["status"] == "success")
    failed = sum(1 for l in leads if l["status"] == "failed")
    duplicates = sum(1 for l in leads if l.get("is_duplicate"))
    return {"total": total, "success": success, "failed": failed, "duplicates": duplicates}
