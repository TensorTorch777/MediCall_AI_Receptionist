"""
APScheduler-based reminder system.

When an appointment is booked, `schedule_reminder` adds a one-shot job that
fires 1 hour before the appointment. The job:
  1. Places an outbound reminder call via Fonoster
  2. Sends a reminder email via SendGrid
  3. Marks reminder_sent = TRUE in the Appointments sheet
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
    return _scheduler


def start_scheduler() -> None:
    sched = _get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("APScheduler started")


def shutdown_scheduler() -> None:
    sched = _get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("APScheduler shut down")


def _execute_reminder(
    appointment_id: str,
    patient_name: str,
    patient_id: str,
    doctor_name: str,
    appointment_datetime: datetime,
) -> None:
    """
    Runs at T-1hr. Sends outbound call + email, then updates the sheet.
    Each step is wrapped so a single failure doesn't block the others.
    """
    from services.sheets import get_patient_by_id, mark_reminder_sent
    from services.fonoster_calls import place_reminder_call
    from services.email_service import send_reminder_email

    logger.info("Executing reminder for appointment %s", appointment_id)

    patient = get_patient_by_id(patient_id)
    if not patient:
        logger.error("Patient %s not found — skipping reminder", patient_id)
        return

    phone = patient["phone"]
    email = patient["email"]

    # 1. Outbound call
    try:
        place_reminder_call(
            phone_number=phone,
            patient_name=patient_name,
            doctor_name=doctor_name,
            appointment_datetime=appointment_datetime,
        )
    except Exception as exc:
        logger.error("Reminder call failed for %s: %s", appointment_id, exc)

    # 2. Email
    try:
        send_reminder_email(
            to_email=email,
            patient_name=patient_name,
            doctor_name=doctor_name,
            appointment_datetime=appointment_datetime,
        )
    except Exception as exc:
        logger.error("Reminder email failed for %s: %s", appointment_id, exc)

    # 3. Update sheet
    try:
        mark_reminder_sent(appointment_id)
    except Exception as exc:
        logger.error("Failed to mark reminder sent for %s: %s", appointment_id, exc)


def schedule_reminder(
    appointment_id: str,
    patient_name: str,
    patient_id: str,
    doctor_name: str,
    appointment_datetime: datetime,
) -> None:
    """
    Schedule a one-shot job 1 hour before the appointment.
    If the appointment is less than 1 hour away, fire immediately.
    """
    sched = _get_scheduler()
    fire_at = appointment_datetime - timedelta(hours=1)

    if fire_at <= datetime.now():
        fire_at = datetime.now() + timedelta(seconds=10)
        logger.warning(
            "Appointment %s is < 1hr away — reminder will fire in 10s",
            appointment_id,
        )

    job_id = f"reminder-{appointment_id}"
    sched.add_job(
        _execute_reminder,
        trigger="date",
        run_date=fire_at,
        id=job_id,
        replace_existing=True,
        kwargs={
            "appointment_id": appointment_id,
            "patient_name": patient_name,
            "patient_id": patient_id,
            "doctor_name": doctor_name,
            "appointment_datetime": appointment_datetime,
        },
    )
    logger.info(
        "Scheduled reminder %s to fire at %s",
        job_id,
        fire_at.isoformat(),
    )
