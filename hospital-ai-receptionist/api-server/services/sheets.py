"""
Google Sheets helpers — all reads and writes to the Patients and Appointments sheets.

Uses gspread with a service-account credentials JSON file.
"""
import logging
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from config import settings

logger = logging.getLogger("sheets")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client: Optional[gspread.Client] = None


def _get_client() -> gspread.Client:
    """Lazily initialise and cache the gspread client."""
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS_JSON,
            scopes=SCOPES,
        )
        _client = gspread.authorize(creds)
        logger.info("Google Sheets client initialised")
    return _client


def _get_sheet(name: str) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(settings.GOOGLE_SPREADSHEET_ID)
    return spreadsheet.worksheet(name)


# ── Patients sheet ────────────────────────────────────────────────────────────

def find_patient_by_name(name: str) -> Optional[dict]:
    """Case-insensitive search for a patient by full_name. Returns the first match."""
    ws = _get_sheet("Patients")
    records = ws.get_all_records()
    target = name.strip().lower()

    for row in records:
        if str(row.get("full_name", "")).strip().lower() == target:
            return {
                "patient_id": str(row["patient_id"]),
                "full_name": str(row["full_name"]),
                "phone": str(row["phone"]),
                "email": str(row["email"]),
            }
    return None


def add_patient(patient_id: str, full_name: str, phone: str, email: str) -> None:
    """Append a new row to the Patients sheet."""
    ws = _get_sheet("Patients")
    ws.append_row(
        [patient_id, full_name, phone, email, datetime.utcnow().isoformat()],
        value_input_option="RAW",
    )
    logger.info("Added patient %s (%s)", patient_id, full_name)


def update_patient(
    patient_id: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """Update phone and/or email for an existing patient by patient_id."""
    ws = _get_sheet("Patients")
    records = ws.get_all_records()

    for idx, row in enumerate(records):
        if str(row.get("patient_id", "")) == patient_id:
            row_number = idx + 2  # +1 for header, +1 for 1-based indexing
            if phone:
                ws.update_cell(row_number, 3, phone)
            if email:
                ws.update_cell(row_number, 4, email)
            logger.info("Updated patient %s", patient_id)
            return

    logger.warning("Patient %s not found for update", patient_id)


# ── Appointments sheet ────────────────────────────────────────────────────────

def add_appointment(
    appointment_id: str,
    patient_id: str,
    patient_name: str,
    doctor_name: str,
    symptoms: str,
    appointment_datetime: datetime,
) -> None:
    """Append a new row to the Appointments sheet."""
    ws = _get_sheet("Appointments")
    ws.append_row(
        [
            appointment_id,
            patient_id,
            patient_name,
            doctor_name,
            symptoms,
            appointment_datetime.isoformat(),
            "FALSE",
            datetime.utcnow().isoformat(),
        ],
        value_input_option="USER_ENTERED",
    )
    logger.info("Added appointment %s for patient %s", appointment_id, patient_id)


def mark_reminder_sent(appointment_id: str) -> None:
    """Set reminder_sent = TRUE for the given appointment."""
    ws = _get_sheet("Appointments")
    records = ws.get_all_records()

    for idx, row in enumerate(records):
        if str(row.get("appointment_id", "")) == appointment_id:
            row_number = idx + 2
            ws.update_cell(row_number, 7, "TRUE")
            logger.info("Marked reminder sent for %s", appointment_id)
            return

    logger.warning("Appointment %s not found for reminder update", appointment_id)


def get_patient_by_id(patient_id: str) -> Optional[dict]:
    """Look up a patient row by patient_id."""
    ws = _get_sheet("Patients")
    records = ws.get_all_records()

    for row in records:
        if str(row.get("patient_id", "")) == patient_id:
            return {
                "patient_id": str(row["patient_id"]),
                "full_name": str(row["full_name"]),
                "phone": str(row["phone"]),
                "email": str(row["email"]),
            }
    return None
