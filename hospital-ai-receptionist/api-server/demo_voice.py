"""
Voice-based Hospital AI Receptionist Demo.
Speak into your mic → AI thinks → Aria speaks back through your speakers.

Run:  python demo_voice.py
"""
import asyncio
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime

import edge_tts
import pygame
import speech_recognition as sr
from dateutil import parser as dateparser

from services.personaplex import generate_response, _get_client, _get_system_prompt
from services.sheets import find_patient_by_name, add_patient, add_appointment

VOICE = "en-US-JennyNeural"

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

EXTRACTION_PROMPT = (
    "Based on the conversation so far, extract any information the patient has provided. "
    "IMPORTANT RULES:\n"
    '- For email: convert spoken forms like "at the rate" or "at rate" to "@", '
    'remove all spaces between parts, produce a valid email (e.g. "vadgaonkarnimish@gmail.com")\n'
    '- For phone: digits only, no dashes (e.g. "8766816208")\n'
    '- For doctor_name: if no specific doctor was named but an appointment was discussed, use "General Physician"\n'
    '- For appointment_datetime: use ISO-like format if possible (e.g. "2026-03-27 18:00")\n'
    'Return ONLY a JSON object: '
    '{"full_name": str|null, "phone": str|null, "email": str|null, '
    '"doctor_name": str|null, "symptoms": str|null, "appointment_datetime": str|null}'
)


def init_audio():
    pygame.mixer.init()


def speak(text: str):
    """Convert text to speech using Edge TTS and play it."""
    async def _tts():
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(tmp_path)
        return tmp_path

    tmp_path = asyncio.run(_tts())
    try:
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
    finally:
        pygame.mixer.music.unload()
        os.unlink(tmp_path)


def listen(recognizer: sr.Recognizer, mic: sr.Microphone) -> str | None:
    """Listen to the microphone and return transcribed text."""
    print(f"  {GREEN}🎤 Listening...{RESET}", end="", flush=True)
    try:
        audio = recognizer.listen(mic, timeout=8, phrase_time_limit=15)
        print(f"\r  {DIM}🔄 Transcribing...{RESET}   ", end="", flush=True)
        text = recognizer.recognize_google(audio)
        print(f"\r  {GREEN}You:{RESET}  {text}          ")
        return text
    except sr.WaitTimeoutError:
        print(f"\r  {YELLOW}(no speech detected — try again){RESET}          ")
        return None
    except sr.UnknownValueError:
        print(f"\r  {YELLOW}(couldn't understand — try again){RESET}          ")
        return None
    except sr.RequestError as e:
        print(f"\r  {RED}(speech recognition error: {e}){RESET}          ")
        return None


def extract_info(history: list[dict]) -> dict:
    client = _get_client()
    msgs = (
        [{"role": "system", "content": _get_system_prompt()}]
        + history
        + [{"role": "user", "content": EXTRACTION_PROMPT}]
    )
    try:
        resp = client.chat_completion(messages=msgs, max_tokens=200, temperature=0.1)
        raw = resp.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


def clean_extracted(info: dict) -> dict:
    """Post-process LLM extraction to fix common speech-to-text artifacts."""
    cleaned = dict(info)

    email = cleaned.get("email") or ""
    if email:
        email = email.lower().strip()
        email = re.sub(r"\s*(at the rate|at rate|at-the-rate)\s*", "@", email)
        email = re.sub(r"\s+at\s+", "@", email)
        email = re.sub(r"\s*(dot|\.)\s*", ".", email)
        email = email.replace(" ", "")
        cleaned["email"] = email

    phone = cleaned.get("phone") or ""
    if phone:
        digits = re.sub(r"[^\d+]", "", phone)
        cleaned["phone"] = digits

    if not cleaned.get("doctor_name") and cleaned.get("appointment_datetime"):
        cleaned["doctor_name"] = "General Physician"

    return cleaned


def save_to_sheets(info: dict):
    info = clean_extracted(info)
    name = info.get("full_name")
    if not name:
        print(f"  {YELLOW}[!] No patient name found — skipping save{RESET}")
        return

    existing = find_patient_by_name(name)
    if existing:
        patient_id = existing["patient_id"]
        print(f"  {CYAN}[sheets] Found existing patient: {name} (ID: {patient_id}){RESET}")
    else:
        patient_id = str(uuid.uuid4())[:8]
        phone = info.get("phone") or "+0000000000"
        email = info.get("email") or "not_provided@example.com"
        add_patient(patient_id=patient_id, full_name=name, phone=phone, email=email)
        print(f"  {GREEN}[sheets] Registered NEW patient: {name} (ID: {patient_id}){RESET}")

    doctor = info.get("doctor_name")
    symptoms = info.get("symptoms") or "Not specified"
    dt_str = info.get("appointment_datetime")

    if dt_str:
        if not doctor:
            doctor = "General Physician"
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
            f"  {GREEN}[sheets] Booked: {appointment_id} — {doctor} on "
            f"{appt_dt.strftime('%B %d, %Y at %I:%M %p')}{RESET}"
        )
    else:
        print(f"  {YELLOW}[sheets] No appointment time found — skipping booking{RESET}")


def main():
    print(f"\n{BOLD}{'='*62}{RESET}")
    print(f"{BOLD}  City Hospital — Voice AI Receptionist{RESET}")
    print(f"{DIM}  Powered by NVIDIA PersonaPlex | Edge TTS | Google Sheets{RESET}")
    print(f"{BOLD}{'='*62}{RESET}")
    print(f"{DIM}  Speak naturally into your microphone.")
    print(f"  Say 'goodbye' or 'quit' to end the conversation.{RESET}")
    print(f"{DIM}  Press Ctrl+C to force quit.{RESET}\n")

    init_audio()
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.5

    try:
        mic = sr.Microphone()
    except (OSError, AttributeError):
        print(f"  {RED}No microphone found! Make sure your mic is connected.{RESET}")
        sys.exit(1)

    with mic as source:
        print(f"  {DIM}Calibrating for ambient noise...{RESET}", end="", flush=True)
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"\r  {GREEN}Microphone ready!{RESET}                    \n")

    history: list[dict] = []

    greeting = generate_response("Hi, I'm calling about an appointment")
    history.append({"role": "user", "content": "Hi, I'm calling about an appointment"})
    history.append({"role": "assistant", "content": greeting})
    print(f"  {BLUE}Aria:{RESET} {greeting}\n")
    speak(greeting)

    while True:
        try:
            with mic as source:
                text = listen(recognizer, source)

            if text is None:
                continue

            lower = text.lower().strip()
            if any(word in lower for word in ["goodbye", "quit", "exit", "bye", "end call"]):
                farewell = (
                    "Thank you for calling City Hospital! "
                    "Have a wonderful day and take care."
                )
                print(f"  {BLUE}Aria:{RESET} {farewell}\n")
                speak(farewell)

                print(f"\n  {DIM}Extracting conversation data...{RESET}")
                info = extract_info(history)
                if info and any(v for v in info.values() if v):
                    print(f"  {CYAN}[extracted]{RESET} {json.dumps(info, indent=2)}")
                    save_to_sheets(info)
                print(f"\n  {BOLD}Session ended.{RESET}\n")
                break

            reply = generate_response(text, history)
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": reply})

            print(f"  {BLUE}Aria:{RESET} {reply}\n")
            speak(reply)

        except KeyboardInterrupt:
            print(f"\n\n  {DIM}Interrupted. Saving data...{RESET}")
            info = extract_info(history)
            if info and any(v for v in info.values() if v):
                print(f"  {CYAN}[extracted]{RESET} {json.dumps(info, indent=2)}")
                save_to_sheets(info)
            print(f"  {BOLD}Session ended.{RESET}\n")
            break


if __name__ == "__main__":
    main()
