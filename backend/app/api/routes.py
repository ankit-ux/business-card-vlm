import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas.lead import BatchResponse, BatchStats, Lead, LeadUpdate
from app.services.excel import leads_to_excel
from app.services.image import preprocess_image, validate_image
from app.services.vlm import VLMError, extract_lead_fields
from app.store import batch_dir, compute_stats, delete_batch, get_batch, recompute_duplicates

router = APIRouter(prefix="/api")


def _lead_from_result(lead_id: str, filename: str, fields: dict | None, error: str | None) -> dict:
    base = {
        "id": lead_id,
        "filename": filename,
        "first_name": "",
        "last_name": "",
        "position": "",
        "company": "",
        "location": "",
        "phone": "",
        "email": "",
        "status": "failed" if error else "success",
        "error": error,
        "is_duplicate": False,
    }
    if fields:
        base.update(fields)
    return base


def _process_one(batch_id: str, file_bytes: bytes, filename: str) -> dict:
    lead_id = str(uuid.uuid4())
    saved_path = batch_dir(batch_id) / f"{lead_id}_{filename}"
    saved_path.write_bytes(file_bytes)

    try:
        processed = preprocess_image(file_bytes)
        fields = extract_lead_fields(processed)
        lead = _lead_from_result(lead_id, filename, fields, None)
    except VLMError as e:
        lead = _lead_from_result(lead_id, filename, None, str(e))
    except Exception as e:  # noqa: BLE001
        lead = _lead_from_result(lead_id, filename, None, f"Unexpected error: {e}")

    return lead, str(saved_path)


@router.post("/upload", response_model=BatchResponse)
async def upload_images(files: list[UploadFile] = File(...), batch_id: str | None = None):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    batch_id = batch_id or str(uuid.uuid4())
    batch = get_batch(batch_id)

    for file in files:
        content = await file.read()
        validate_image(file, content)
        lead, saved_path = _process_one(batch_id, content, file.filename)

        batch["leads"][lead["id"]] = lead
        batch["order"].append(lead["id"])
        batch["files"][lead["id"]] = saved_path

    recompute_duplicates(batch)
    stats = compute_stats(batch)
    leads = [batch["leads"][lid] for lid in batch["order"]]
    return {"batch_id": batch_id, "leads": leads, "stats": stats}


@router.get("/leads/{batch_id}", response_model=BatchResponse)
def get_leads(batch_id: str):
    batch = get_batch(batch_id)
    leads = [batch["leads"][lid] for lid in batch["order"]]
    stats = compute_stats(batch)
    return {"batch_id": batch_id, "leads": leads, "stats": stats}


@router.patch("/leads/{batch_id}/{lead_id}", response_model=Lead)
def update_lead(batch_id: str, lead_id: str, update: LeadUpdate):
    batch = get_batch(batch_id)
    if lead_id not in batch["leads"]:
        raise HTTPException(status_code=404, detail="Lead not found.")

    lead = batch["leads"][lead_id]
    for key, value in update.model_dump(exclude_unset=True).items():
        lead[key] = value

    recompute_duplicates(batch)
    return lead


@router.post("/leads/{batch_id}/retry/{lead_id}", response_model=Lead)
def retry_lead(batch_id: str, lead_id: str):
    batch = get_batch(batch_id)
    if lead_id not in batch["leads"]:
        raise HTTPException(status_code=404, detail="Lead not found.")

    saved_path = batch["files"].get(lead_id)
    if not saved_path:
        raise HTTPException(status_code=400, detail="Original image not available for retry.")

    from pathlib import Path

    content = Path(saved_path).read_bytes()
    filename = batch["leads"][lead_id]["filename"]

    try:
        processed = preprocess_image(content)
        fields = extract_lead_fields(processed)
        updated = _lead_from_result(lead_id, filename, fields, None)
    except VLMError as e:
        updated = _lead_from_result(lead_id, filename, None, str(e))
    except Exception as e:  # noqa: BLE001
        updated = _lead_from_result(lead_id, filename, None, f"Unexpected error: {e}")

    batch["leads"][lead_id] = updated
    recompute_duplicates(batch)
    return updated


@router.delete("/leads/{batch_id}")
def delete_batch_endpoint(batch_id: str):
    delete_batch(batch_id)
    return {"deleted": True, "batch_id": batch_id}


@router.get("/leads/{batch_id}/export")
def export_excel(batch_id: str):
    batch = get_batch(batch_id)
    leads = [batch["leads"][lid] for lid in batch["order"]]
    if not leads:
        raise HTTPException(status_code=400, detail="No leads to export for this batch.")

    excel_bytes = leads_to_excel(leads)
    filename = f"leads_{batch_id[:8]}.xlsx"
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/health")
def health():
    import os

    return {"status": "ok", "vlm_provider": os.getenv("VLM_PROVIDER", "dashscope")}
