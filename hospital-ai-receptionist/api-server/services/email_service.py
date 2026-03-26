"""
SendGrid email service for appointment reminders.
"""
import logging
from datetime import datetime

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from config import settings

logger = logging.getLogger("email_service")


def _build_reminder_html(
    patient_name: str,
    doctor_name: str,
    appointment_datetime: datetime,
) -> str:
    time_str = appointment_datetime.strftime("%I:%M %p")
    date_str = appointment_datetime.strftime("%A, %B %d, %Y")

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;
                border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background: #1a73e8; color: white; padding: 20px 24px;">
            <h2 style="margin: 0;">City Hospital — Appointment Reminder</h2>
        </div>
        <div style="padding: 24px;">
            <p>Dear <strong>{patient_name}</strong>,</p>
            <p>This is a friendly reminder that you have an upcoming appointment:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555;">Doctor</td>
                    <td style="padding: 8px;">Dr. {doctor_name}</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 8px; font-weight: bold; color: #555;">Date</td>
                    <td style="padding: 8px;">{date_str}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555;">Time</td>
                    <td style="padding: 8px;">{time_str}</td>
                </tr>
            </table>
            <p>Please arrive <strong>10 minutes early</strong> and bring any relevant
               medical documents or previous prescriptions.</p>
            <p style="color: #888; font-size: 13px; margin-top: 24px;">
                If you need to reschedule, please call us at (555) 123-4567.
            </p>
        </div>
        <div style="background: #f5f5f5; padding: 12px 24px; text-align: center;
                    font-size: 12px; color: #999;">
            City Hospital &bull; 123 Health Ave &bull; contact@cityhospital.com
        </div>
    </div>
    """


def send_reminder_email(
    to_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_datetime: datetime,
) -> None:
    """Send an HTML reminder email via SendGrid."""
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping email to %s", to_email)
        return

    html_body = _build_reminder_html(patient_name, doctor_name, appointment_datetime)
    date_str = appointment_datetime.strftime("%B %d at %I:%M %p")

    message = Mail(
        from_email=Email(settings.SENDGRID_FROM_EMAIL, "City Hospital"),
        to_emails=To(to_email),
        subject=f"Appointment Reminder — Dr. {doctor_name} on {date_str}",
    )
    message.content = [Content("text/html", html_body)]

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(
            "Reminder email sent to %s (status %s)", to_email, response.status_code
        )
    except Exception as exc:
        logger.error("SendGrid email failed for %s: %s", to_email, exc)
        raise
