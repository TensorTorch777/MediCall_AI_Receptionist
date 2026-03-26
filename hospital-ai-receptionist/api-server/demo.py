"""
Interactive demo: Hospital AI Receptionist
Shows PersonaPlex (LLM) conversation + Google Sheets data storage.
Run: python demo.py
"""
import json
import re
import sys
import uuid
from datetime import datetime

from dateutil import parser as dateparser

from services.personaplex import generate_response
from services.sheets import (
    find_patient_by_name,
    add_patient,
    add_appointment,
)

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

EXTRACTION_PROMPT = """Based on the conversation so far, extract any information the patient has provided.
Return ONLY a JSON object with these fields (use null for unknown):
{"full_name": str|null, "phone": str|null, "email": str|null, "doctor_name": str|null, "symptoms": str|null, "appointment_datetime": str|null}
Do not include any other text, just the JSON."""


def extract_info(history: list[dict]) -> dict:
    """Ask the LLM to extract structured data from the conversation."""
    extraction_messages = history.copy()
    extraction_messages.append({"role": "user", "content": EXTRACTION_PROMPT})

    from services.personaplex import _get_client, _get_system_prompt
    client = _get_client()

    try:
        resp = client.chat_completion(
            messages=[{"role": "system", "content": _get_system_prompt()}]
            + extraction_messages,
            max_tokens=200,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


def print_banner():
    print(f"\n{BOLD}{'='*62}{RESET}")
    print(f"{BOLD}  City Hospital — AI Receptionist Demo{RESET}")
    print(f"{DIM}  Powered by NVIDIA PersonaPlex | Data stored in Google Sheets{RESET}")
    print(f"{BOLD}{'='*62}{RESET}")
    print(f"{DIM}  Type your messages as if you're a patient calling the hospital.")
    print(f"  Type 'quit' to end  |  Type 'save' to register & book now{RESET}\n")


def save_to_sheets(info: dict) -> tuple[str | None, str | None]:
    """Register patient and book appointment in Google Sheets."""
    patient_id = None
    appointment_id = None

    name = info.get("full_name")
    if not name:
        print(f"  {YELLOW}[!] No patient name found in conversation — skipping save{RESET}")
        return None, None

    existing = find_patient_by_name(name)
    if existing:
        patient_id = existing["patient_id"]
        print(f"  {DIM}[sheets] Found existing patient: {name} (ID: {patient_id}){RESET}")
    else:
        patient_id = str(uuid.uuid4())[:8]
        phone = info.get("phone") or "+0000000000"
        email = info.get("email") or "not_provided@example.com"
        add_patient(patient_id=patient_id, full_name=name, phone=phone, email=email)
        print(f"  {GREEN}[sheets] Registered new patient: {name} (ID: {patient_id}){RESET}")

    doctor = info.get("doctor_name")
    symptoms = info.get("symptoms") or "Not specified"
    dt_str = info.get("appointment_datetime")

    if doctor and dt_str:
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
            patient_name=name,
            doctor_name=doctor,
            symptoms=symptoms,
            appointment_datetime=appt_dt,
        )
        print(
            f"  {GREEN}[sheets] Booked appointment {appointment_id} with {doctor} "
            f"on {appt_dt.strftime('%B %d, %Y at %I:%M %p')}{RESET}"
        )
    elif doctor:
        print(f"  {YELLOW}[sheets] Doctor noted ({doctor}) but no date/time yet — appointment not booked{RESET}")
    else:
        print(f"  {YELLOW}[sheets] No doctor/time info — appointment not booked{RESET}")

    return patient_id, appointment_id


def main():
    print_banner()

    history: list[dict] = []

    greeting = generate_response("Hi")
    history.append({"role": "user", "content": "Hi"})
    history.append({"role": "assistant", "content": greeting})
    print(f"  {BLUE}Aria:{RESET} {greeting}\n")

    while True:
        try:
            user_input = input(f"  {GREEN}You:{RESET}  ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print(f"\n  {DIM}Extracting conversation data...{RESET}")
            info = extract_info(history)
            if info:
                print(f"  {CYAN}[extracted]{RESET} {json.dumps(info, indent=2)}")
                save_to_sheets(info)
            print(f"\n  {BOLD}Thank you for using City Hospital AI Receptionist!{RESET}\n")
            break

        if user_input.lower() == "save":
            print(f"\n  {DIM}Extracting data from conversation...{RESET}")
            info = extract_info(history)
            if info:
                print(f"  {CYAN}[extracted]{RESET} {json.dumps(info, indent=2)}")
                save_to_sheets(info)
            print()
            continue

        reply = generate_response(user_input, history)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        print(f"  {BLUE}Aria:{RESET} {reply}\n")


if __name__ == "__main__":
    main()
