"""One-time setup: create Patients and Appointments sheets with headers."""
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID = "1sADXgEcHoiYfi8JL5zzpfw8778Ezg_2NBFj7ec6kLoA"

PATIENTS_HEADERS = ["patient_id", "full_name", "phone", "email", "registered_at"]
APPOINTMENTS_HEADERS = [
    "appointment_id", "patient_id", "patient_name", "doctor_name",
    "symptoms", "appointment_datetime", "reminder_sent", "created_at"
]


def main():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    existing = [ws.title for ws in spreadsheet.worksheets()]
    print(f"Existing sheets: {existing}")

    # Create or update Patients sheet
    if "Patients" not in existing:
        ws = spreadsheet.add_worksheet(title="Patients", rows=1000, cols=len(PATIENTS_HEADERS))
        ws.update([PATIENTS_HEADERS], value_input_option="RAW")
        print("Created 'Patients' sheet with headers")
    else:
        print("'Patients' sheet already exists")

    # Create or update Appointments sheet
    if "Appointments" not in existing:
        ws = spreadsheet.add_worksheet(title="Appointments", rows=1000, cols=len(APPOINTMENTS_HEADERS))
        ws.update([APPOINTMENTS_HEADERS], value_input_option="RAW")
        print("Created 'Appointments' sheet with headers")
    else:
        print("'Appointments' sheet already exists")

    # Remove default Sheet1 if it exists and we have our sheets
    updated = [ws.title for ws in spreadsheet.worksheets()]
    if "Sheet1" in updated and len(updated) > 1:
        default = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(default)
        print("Removed default 'Sheet1'")

    print("\nDone! Sheets are ready.")
    for ws in spreadsheet.worksheets():
        print(f"  - {ws.title} ({ws.row_count} rows x {ws.col_count} cols)")


if __name__ == "__main__":
    main()
