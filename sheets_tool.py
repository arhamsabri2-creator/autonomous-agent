from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets"
]
CREDS_FILE = "gmail_credentials.json"
TOKEN_FILE = "gmail_token.json"
SHEET_ID = "1YkIXvLjGW6S6GBM_pZHqaqmnTHFDuiOyEyCieGo_i5c"

def get_sheets_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    service = build("sheets", "v4", credentials=creds)
    return service

def log_job_to_sheet(title, company, platform, link, status="Applied"):
    service = get_sheets_service()
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    values = [[date, title, company, platform, link, status]]
    body = {"values": values}
    result = service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="Sheet1!A:F",
        valueInputOption="RAW",
        body=body
    ).execute()
    print(f"Job logged to sheet: {title} at {company}")
    return result

if __name__ == "__main__":
    log_job_to_sheet(
        title="Test Python Internship",
        company="Test Company",
        platform="Internshala",
        link="https://internshala.com/test",
        status="Applied"
    )