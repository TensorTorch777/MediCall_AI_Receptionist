"""
Conversation routes called by the Fonoster VoiceServer during a live call.
Each endpoint corresponds to a step in the call flow.
"""
import logging
import re
import uuid
from datetime import datetime

from dateutil import parser as dateparser
from fastapi import APIRouter, HTTPException

from models.patient import (
    BookRequest,
    BookResponse,
    ChatRequest,
    ChatResponse,
    FinalizeRequest,
    FinalizeResponse,
    LookupRequest,
    LookupResponse,
    RegisterRequest,
    RegisterResponse,
    UpdateRequest,
    UpdateResponse,
)
from services.personaplex import generate_response
from services.sheets import (
    find_patient_by_name,
    add_patient,
    update_patient,
    add_appointment,
    mark_reminder_sent,
)
from services.scheduler import schedule_reminder

logger = logging.getLogger("conversation")
router = APIRouter()


@router.post("/lookup", response_model=LookupResponse)
async def lookup_patient(req: LookupRequest):
    """Search the Patients sheet by name (case-insensitive)."""
    logger.info("Lookup request for name=%s call_id=%s", req.name, req.call_id)

    try:
        patient = find_patient_by_name(req.name)
    except Exception as exc:
        logger.error("Sheets lookup failed: %s", exc)
        raise HTTPException(status_code=502, detail="Database unavailable") from exc

    if patient:
        return LookupResponse(
            found=True,
            patient_id=patient["patient_id"],
            full_name=patient["full_name"],
            phone=patient["phone"],
            email=patient["email"],
        )
    return LookupResponse(found=False)


@router.post("/register", response_model=RegisterResponse)
async def register_patient(req: RegisterRequest):
    """Register a brand-new patient — writes a row to the Patients sheet."""
    patient_id = str(uuid.uuid4())[:8]
    logger.info("Registering patient %s (id=%s)", req.full_name, patient_id)

    try:
        add_patient(
            patient_id=patient_id,
            full_name=req.full_name,
            phone=req.phone,
            email=req.email,
        )
    except Exception as exc:
        logger.error("Sheets write failed: %s", exc)
        raise HTTPException(status_code=502, detail="Database write failed") from exc

    return RegisterResponse(patient_id=patient_id, success=True)


@router.post("/update", response_model=UpdateResponse)
async def update_patient_info(req: UpdateRequest):
    """Update phone/email for an existing patient."""
    logger.info("Updating patient %s", req.patient_id)

    try:
        update_patient(
            patient_id=req.patient_id,
            phone=req.phone,
            email=req.email,
        )
    except Exception as exc:
        logger.error("Sheets update failed: %s", exc)
        raise HTTPException(status_code=502, detail="Database update failed") from exc

    return UpdateResponse(success=True)


@router.post("/book", response_model=BookResponse)
async def book_appointment(req: BookRequest):
    """
    Book an appointment:
      1. Parse the natural-language datetime
      2. Write a row to the Appointments sheet
      3. Schedule an APScheduler reminder at T-1 hr
    """
    logger.info(
        "Booking for patient=%s doctor=%s at=%s",
        req.patient_name,
        req.doctor_name,
        req.appointment_datetime,
    )

    # Parse the spoken datetime into an actual datetime object
    try:
        appt_dt = dateparser.parse(req.appointment_datetime, fuzzy=True)
        if appt_dt is None:
            raise ValueError("Could not parse datetime")
        # If no year provided and parsed date is in the past, bump to next year
        if appt_dt < datetime.now():
            appt_dt = appt_dt.replace(year=appt_dt.year + 1)
    except (ValueError, OverflowError):
        logger.warning("Unparseable datetime, falling back to raw string")
        appt_dt = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    appointment_id = "APT-" + str(uuid.uuid4())[:8].upper()

    try:
        add_appointment(
            appointment_id=appointment_id,
            patient_id=req.patient_id,
            patient_name=req.patient_name,
            doctor_name=req.doctor_name,
            symptoms=req.symptoms,
            appointment_datetime=appt_dt,
        )
    except Exception as exc:
        logger.error("Sheets write failed: %s", exc)
        raise HTTPException(status_code=502, detail="Appointment write failed") from exc

    # Schedule a reminder 1 hour before
    try:
        schedule_reminder(
            appointment_id=appointment_id,
            patient_name=req.patient_name,
            patient_id=req.patient_id,
            doctor_name=req.doctor_name,
            appointment_datetime=appt_dt,
        )
    except Exception as exc:
        logger.error("Scheduler error (non-fatal): %s", exc)

    return BookResponse(
        appointment_id=appointment_id,
        appointment_datetime=appt_dt.strftime("%B %d, %Y at %I:%M %p"),
        success=True,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_receptionist(req: ChatRequest):
    """Lightweight chat endpoint for web/mobile UI demos."""
    try:
        reply = generate_response(req.message, req.history)
    except Exception as exc:
        logger.error("Chat generation failed: %s", exc)
        raise HTTPException(status_code=502, detail="AI unavailable") from exc
    return ChatResponse(reply=reply)


def _clean_extracted(info: dict) -> dict:
    cleaned = dict(info or {})
    email = str(cleaned.get("email") or "").lower().strip()
    if email:
        email = re.sub(r"\s*(at the rate|at rate|at-the-rate)\s*", "@", email)
        email = re.sub(r"\s+at\s+", "@", email)
        email = re.sub(r"\s*(dot|\.)\s*", ".", email)
        email = email.replace(" ", "")
        cleaned["email"] = email

    phone = str(cleaned.get("phone") or "")
    if phone:
        cleaned["phone"] = re.sub(r"[^\d+]", "", phone)

    if not cleaned.get("doctor_name") and cleaned.get("appointment_datetime"):
        cleaned["doctor_name"] = "General Physician"

    return cleaned


@router.post("/finalize", response_model=FinalizeResponse)
async def finalize_conversation(req: FinalizeRequest):
    """Extract patient details from history and persist to Google Sheets."""
    extraction_prompt = (
        "Extract patient booking details from this conversation. "
        "Return ONLY JSON with keys: full_name, phone, email, doctor_name, symptoms, appointment_datetime. "
        "If doctor is not explicitly named but booking intent exists, use General Physician. "
        "Normalize email to valid form and phone to digits only."
    )
    try:
        extraction = generate_response(extraction_prompt, req.history)
        import json

        start = extraction.find("{")
        end = extraction.rfind("}")
        parsed = {}
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(extraction[start : end + 1])
        parsed = _clean_extracted(parsed)
    except Exception as exc:
        logger.error("Finalize extraction failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to extract conversation details") from exc

    full_name = parsed.get("full_name")
    if not full_name:
        return FinalizeResponse(success=False, extracted=parsed)

    patient = find_patient_by_name(full_name)
    if patient:
        patient_id = patient["patient_id"]
    else:
        patient_id = str(uuid.uuid4())[:8]
        add_patient(
            patient_id=patient_id,
            full_name=full_name,
            phone=parsed.get("phone") or "+0000000000",
            email=parsed.get("email") or "not_provided@example.com",
        )

    appointment_id = None
    dt_str = parsed.get("appointment_datetime")
    if dt_str:
        try:
            appt_dt = dateparser.parse(dt_str, fuzzy=True)
            if appt_dt and appt_dt < datetime.now():
                appt_dt = appt_dt.replace(year=appt_dt.year + 1)
        except (ValueError, OverflowError):
            appt_dt = None
        if appt_dt is None:
            appt_dt = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        appointment_id = "APT-" + str(uuid.uuid4())[:8].upper()
        add_appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            patient_name=full_name,
            doctor_name=parsed.get("doctor_name") or "General Physician",
            symptoms=parsed.get("symptoms") or "Not specified",
            appointment_datetime=appt_dt,
        )

    return FinalizeResponse(
        success=True,
        extracted=parsed,
        patient_id=patient_id,
        appointment_id=appointment_id,
    )
