"""Checks that the saved Google token works. Run: python -m scripts.check_drive"""
from swingbot.reports.google_drive import get_drive_service

if __name__ == "__main__":
    result = get_drive_service().files().list(pageSize=10, fields="files(id, name)").execute()
    print("Google Drive работает!")
    print(result.get("files", []))
