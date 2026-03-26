"""
Outbound reminder calls via the Fonoster VoiceServer.

The API server tells the Node.js VoiceServer to place an outbound call
by hitting a /reminder-call endpoint exposed on the VoiceServer.  The
VoiceServer then uses Fonoster SDK verbs to dial the patient and play
the reminder message.

If the VoiceServer exposes no such endpoint, we fall back to making a
direct Fonoster REST API call (requires FONOSTER_ACCESS_KEY_ID/SECRET).
"""
import logging
from datetime import datetime

import httpx

from config import settings

logger = logging.getLogger("fonoster_calls")


def place_reminder_call(
    phone_number: str,
    patient_name: str,
    doctor_name: str,
    appointment_datetime: datetime,
) -> None:
    """
    Ask the VoiceServer to dial the patient with a TTS reminder.

    Falls back to logging if the voice server is unreachable (so the email
    reminder can still go out).
    """
    time_str = appointment_datetime.strftime("%I:%M %p")
    date_str = appointment_datetime.strftime("%B %d, %Y")

    message = (
        f"Hello {patient_name}, this is a reminder from City Hospital. "
        f"You have an appointment with Doctor {doctor_name} "
        f"on {date_str} at {time_str}, which is in about one hour. "
        f"Please arrive 10 minutes early. Thank you!"
    )

    payload = {
        "phone_number": phone_number,
        "message": message,
    }

    try:
        response = httpx.post(
            f"{settings.VOICE_SERVER_URL}/reminder-call",
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        logger.info("Reminder call placed to %s", phone_number)
    except httpx.HTTPError as exc:
        logger.error(
            "VoiceServer reminder-call failed for %s: %s — "
            "the patient will still receive an email reminder",
            phone_number,
            exc,
        )
        raise
