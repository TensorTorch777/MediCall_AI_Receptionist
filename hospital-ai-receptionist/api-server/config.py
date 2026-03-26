import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    HF_API_KEY: str = os.getenv("HF_API_KEY", "")
    HF_PERSONAPLEX_MODEL: str = os.getenv("HF_PERSONAPLEX_MODEL", "nvidia/personaplex")

    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "receptionist@cityhospital.com")

    GOOGLE_SHEETS_CREDENTIALS_JSON: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "credentials.json")
    GOOGLE_SPREADSHEET_ID: str = os.getenv("GOOGLE_SPREADSHEET_ID", "")

    FONOSTER_ACCESS_KEY_ID: str = os.getenv("FONOSTER_ACCESS_KEY_ID", "")
    FONOSTER_ACCESS_KEY_SECRET: str = os.getenv("FONOSTER_ACCESS_KEY_SECRET", "")
    FONOSTER_API_ENDPOINT: str = os.getenv("FONOSTER_API_ENDPOINT", "localhost:50051")

    VOICE_SERVER_URL: str = os.getenv("VOICE_SERVER_URL", "http://localhost:50061")


settings = Settings()
