"""Pydantic request schemas and shared helpers for Track B routers."""
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pydantic import BaseModel, Field


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_project_oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(400, "Invalid project ID")


def get_upload_dir() -> Path:
    main_mod = sys.modules.get("main")
    if main_mod is not None and hasattr(main_mod, "UPLOAD_DIR"):
        return Path(main_mod.UPLOAD_DIR).resolve()
    return Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()


def serialize_doc(doc):
    if doc is None:
        return None
    copy = dict(doc)
    if "_id" in copy:
        copy["_id"] = str(copy["_id"])
    return copy


def serialize_docs(docs):
    return [serialize_doc(d) for d in docs]


class MappingAnalyzeRequest(BaseModel):
    job_id: str | None = None
    min_confidence: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.55, ge=0.1, le=0.95)
    min_overlap: float = Field(default=0.2, ge=0.0, le=1.0)
    enable_cross_image_registration: bool = False
    auto_pair_registration: bool = False
    max_time_window_hours: float = Field(default=24.0, gt=0.0)


class AutoRegistrationRequest(BaseModel):
    minimum_matches: int = Field(default=12, ge=4, le=100)
    max_time_diff_seconds: float = Field(default=10.0, ge=0.0)
    max_gps_meters: float = Field(default=15.0, ge=0.0)


class AssociationAnalyzeRequest(BaseModel):
    job_id: str | None = None
    min_overlap: float = Field(default=0.2, ge=0.0, le=1.0)
    max_time_window_hours: float = Field(default=24.0, gt=0.0)
