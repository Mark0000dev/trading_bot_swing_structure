"""Uploads the last 50 trades of a table to Google Drive as a CSV (the same file is updated each time)."""
import io
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from swingbot.config import DATA_DIR, GOOGLE_SCOPES, GOOGLE_TOKEN_FILE
from swingbot.database import read_sql

# report name -> (table, file that stores the Drive file id, file name on Drive)
REPORTS = {
    "paper": ("trading_paper", DATA_DIR / "drive_file_id.txt", "last_50_trades.csv"),
    "third": ("third_option", DATA_DIR / "drive_file_id_third.txt", "last_50_trades_third_option.csv"),
}


def get_drive_service():
    creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), GOOGLE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GOOGLE_TOKEN_FILE.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def get_trades(table: str):
    return read_sql(f"""
        SELECT
            NOW() AS report_updated_at,
            id, symbol, direction,
            time_open, time_closed,
            price_open, price_closed,
            pnl_percentage, duration_hours
        FROM {table}
        ORDER BY time_open DESC NULLS LAST, id DESC
        LIMIT 50
    """)


def upload_csv(service, df, file_id_path, file_name):
    media = MediaIoBaseUpload(io.BytesIO(df.to_csv(index=False).encode("utf-8-sig")),
                              mimetype="text/csv", resumable=True)

    file_id = file_id_path.read_text().strip() if os.path.exists(file_id_path) else ""
    if file_id:
        try:
            service.files().update(fileId=file_id, media_body=media).execute()
            print("CSV обновлён на Google Drive")
            return
        except Exception as e:
            print(f"Не удалось обновить файл: {e}")

    result = service.files().create(body={"name": file_name, "mimeType": "text/csv"},
                                    media_body=media, fields="id").execute()
    os.makedirs(file_id_path.parent, exist_ok=True)
    file_id_path.write_text(result["id"])
    print("CSV создан на Google Drive")


def run_report(report: str):
    table, file_id_path, file_name = REPORTS[report]
    df = get_trades(table)
    upload_csv(get_drive_service(), df, file_id_path, file_name)
    print(f"[{report}] Выгружено сделок: {len(df)}")
