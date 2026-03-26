# MediCall_AI_Receptionist

MediCall_AI_Receptionist is a voice-first hospital receptionist demo powered by NVIDIA PersonaPlex. It conducts natural patient conversations, captures booking details, and stores records in Google Sheets.

The current demo is optimized for local execution with:
- `api-server` for AI, extraction, and Google Sheets persistence
- `ui` for a polished web interface with microphone input, speech output, and an animated orb

## PersonaPlex

PersonaPlex is the core model concept behind this project's conversational behavior.

- Model family: NVIDIA PersonaPlex
- Intended capability: real-time, full-duplex speech conversation
- In this repo:
  - `services/personaplex.py` is the integration layer
  - `prompts/receptionist.txt` defines the hospital receptionist persona and guardrails

### Runtime Note

PersonaPlex is a speech-to-speech model that typically runs on GPU infrastructure.  
For this local demo pipeline, the conversation layer uses a compatible Hugging Face chat model path through the same `personaplex.py` service contract, so the end-to-end app flow can be tested locally while preserving the PersonaPlex-oriented architecture.

### PersonaPlex References

- Hugging Face model page: [nvidia/personaplex-7b-v1](https://huggingface.co/nvidia/personaplex-7b-v1)
- Project repository: [NVIDIA/personaplex](https://github.com/NVIDIA/personaplex)

## Core Features

- Real-time voice conversation in the browser
- PersonaPlex-oriented receptionist pipeline and prompt orchestration
- AI receptionist behavior with strict non-hallucination prompt rules
- Automatic extraction of:
  - patient name
  - phone
  - email
  - doctor or specialty
  - symptoms
  - appointment date and time
- Automatic save to Google Sheets on conversation completion
- FastAPI backend with structured endpoints

## Architecture

```
Browser UI (mic + speaker)
        |
        v
FastAPI API Server (Python)
  - PersonaPlex integration layer
  - /conversation/chat
  - /conversation/finalize
  - /conversation/register
  - /conversation/book
        |
        v
Google Sheets (Patients, Appointments)
```

## Project Structure

```
hospital-ai-receptionist/
├── api-server/
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── prompts/
│   ├── requirements.txt
│   ├── .env.example
│   └── setup_sheets.py
├── ui/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── voice-server/
│   ├── index.js
│   ├── handlers/
│   ├── package.json
│   └── .env.example
├── legacy/                     # archived debug and SIP setup scripts
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud service account with Sheets API and Drive API enabled
- Hugging Face API token (for the PersonaPlex integration path)
- SendGrid API key (optional for reminder emails)

## Setup

### 1) API server

```bash
cd api-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set values in `api-server/.env`, then place your Google service account key file in `api-server/` and keep:

```env
HF_API_KEY=your_huggingface_token
HF_PERSONAPLEX_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
GOOGLE_SHEETS_CREDENTIALS_JSON=credentials.json
```

### 2) Voice server (optional for call integrations)

```bash
cd ../voice-server
npm install
cp .env.example .env
```

### 3) UI

No build is required. It is static HTML/CSS/JS.

## Running the Demo

Open two terminals.

### Terminal 1: API server

```bash
cd api-server
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: UI server

```bash
cd ui
python3 -m http.server 5500
```

Open `http://localhost:5500`.

Click `Book an Appointment` and speak naturally.  
Say `goodbye` to end and trigger auto-save to Google Sheets.

## Google Sheets Format

Create a spreadsheet with two tabs.

### Patients

| patient_id | full_name | phone | email | registered_at |
|------------|-----------|-------|-------|---------------|

### Appointments

| appointment_id | patient_id | patient_name | doctor_name | symptoms | appointment_datetime | reminder_sent | created_at |
|----------------|------------|--------------|-------------|----------|----------------------|---------------|------------|

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/conversation/chat` | Chat turn via PersonaPlex integration service |
| POST | `/conversation/finalize` | Extract and persist data from full conversation history |
| POST | `/conversation/lookup` | Find patient by name |
| POST | `/conversation/register` | Register patient |
| POST | `/conversation/update` | Update patient contact details |
| POST | `/conversation/book` | Book appointment |

## Security Notes

- Do not commit `.env` files
- Do not commit `api-server/credentials.json`
- Rotate any credentials that were ever exposed in logs or screenshots
- Use `.env.example` files for sharing configuration format

## License

MIT
