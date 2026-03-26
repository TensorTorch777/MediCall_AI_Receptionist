from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────────

class LookupRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Patient's spoken name")
    call_id: str = Field(default="unknown", description="Fonoster call identifier")


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=5)
    email: str = Field(..., min_length=3)


class UpdateRequest(BaseModel):
    patient_id: str
    phone: Optional[str] = None
    email: Optional[str] = None


class BookRequest(BaseModel):
    patient_id: str
    patient_name: str
    doctor_name: str
    symptoms: str
    appointment_datetime: str = Field(
        ...,
        description="Natural-language or ISO datetime string for the appointment",
    )

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Latest user utterance")
    history: list[dict] = Field(default_factory=list, description="Chat history")

class FinalizeRequest(BaseModel):
    history: list[dict] = Field(default_factory=list, description="Conversation history")


# ── Response models ───────────────────────────────────────────────────────────

class LookupResponse(BaseModel):
    found: bool
    patient_id: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class RegisterResponse(BaseModel):
    patient_id: str
    success: bool


class UpdateResponse(BaseModel):
    success: bool


class BookResponse(BaseModel):
    appointment_id: str
    appointment_datetime: str
    success: bool

class ChatResponse(BaseModel):
    reply: str

class FinalizeResponse(BaseModel):
    success: bool
    extracted: dict
    patient_id: Optional[str] = None
    appointment_id: Optional[str] = None


# ── Internal data models ─────────────────────────────────────────────────────

class Patient(BaseModel):
    patient_id: str
    full_name: str
    phone: str
    email: str
    registered_at: datetime = Field(default_factory=datetime.utcnow)


class Appointment(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    doctor_name: str
    symptoms: str
    appointment_datetime: datetime
    reminder_sent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
