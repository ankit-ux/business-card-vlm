from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class LeadStatus(str, Enum):
    success = "success"
    failed = "failed"


class Lead(BaseModel):
    id: str
    filename: str
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    company: str = ""
    location: str = ""
    phone: str = ""
    email: str = ""
    status: LeadStatus
    error: Optional[str] = None
    is_duplicate: bool = False


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class BatchStats(BaseModel):
    total: int = 0
    success: int = 0
    failed: int = 0
    duplicates: int = 0


class BatchResponse(BaseModel):
    batch_id: str
    leads: list[Lead]
    stats: BatchStats
