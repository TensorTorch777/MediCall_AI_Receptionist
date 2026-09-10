# Problem Statement

## Title

Hospital front desks cannot keep up with appointment demand, so patients wait on hold, after-hours callers are missed, and booking details are captured inconsistently.

## Context

City Hospital (and clinics like it) still depend on a small human receptionist team as the first point of contact. Patients call or visit to book appointments, update contact details, describe symptoms, and confirm a doctor or specialty. Those conversations are time-sensitive, emotionally charged, and operationally repetitive.

Staff must collect a complete record every time: full name, phone, email, doctor or specialty, symptoms, and preferred date and time. Incomplete or invented data creates downstream failures in scheduling, reminders, and care coordination.

## The Problem

Front-desk capacity does not scale with call volume. During peak hours, patients wait. After hours and during lunch, many calls go unanswered. When a receptionist is available, conversations are still interrupted, details are typed by hand, and records live in spreadsheets or siloed systems that are easy to skip or mistype.

Existing phone trees and web forms do not solve this. Phone trees feel impersonal and drop callers before a booking is complete. Forms require literacy, device access, and the patient to already know which fields matter. Neither option conducts a natural conversation, confirms details back to the patient, or refuses to guess missing personal data.

Hospitals also cannot safely automate this with an unconstrained chatbot. A receptionist must not diagnose, invent doctor names, autofill phone numbers or emails, or leak other patients' information. Emergency callers need an immediate redirect to 911. Any voice solution that hallucinates records is worse than no automation at all.

## Who Is Affected

- **Patients** who need a timely, calm way to book care without long hold times
- **Reception and scheduling staff** who spend peak hours on repetitive intake instead of exceptions and in-person visitors
- **Clinicians** who receive incomplete or incorrect appointment records
- **Hospital operations** that lose bookings after hours and cannot reliably send reminder calls or emails

## Why It Matters

Missed and incomplete bookings delay care, waste clinic slots, and increase no-shows when reminders never go out. Patients who cannot get through may delay seeking care or go to the emergency department for non-urgent needs. Staff burnout rises when every call is a full intake script. Data errors in name, contact, or appointment time create privacy risk and operational rework.

## Desired Outcome

Patients should be able to speak naturally with a hospital receptionist — in the browser today, and on a phone line later — and complete a booking without waiting for a human to become free.

The assistant should:

- Greet the caller, gather required intake fields, and read them back for confirmation
- Register new patients and look up returning patients without inventing prior records
- Persist confirmed patient and appointment rows (name, phone, email, doctor, symptoms, datetime)
- Stay within strict guardrails: no medical advice, no hallucinated personal data, English-only conversational speech, emergency redirect when needed
- Trigger reminder workflows after a successful booking

Success looks like a complete, confirmed appointment record in the hospital's patient and appointment store after a short voice conversation, with no fabricated fields.

## Scope of This Project

MediCall_AI_Receptionist is a voice-first demo of that receptionist: NVIDIA PersonaPlex-oriented conversation, a FastAPI intake and persistence layer, a browser microphone UI, and Google Sheets as the operational record for patients and appointments.
