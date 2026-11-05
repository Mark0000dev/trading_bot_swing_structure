"""One-time Google Drive OAuth: creates credentials/token.json. Run: python -m scripts.authorize_drive"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

from swingbot.config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_SCOPES, GOOGLE_TOKEN_FILE

if __name__ == "__main__":
    flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CLIENT_SECRET_FILE), GOOGLE_SCOPES)
    credentials = flow.run_local_server(host="0.0.0.0", port=8080, open_browser=False)

    os.makedirs(GOOGLE_TOKEN_FILE.parent, exist_ok=True)
    GOOGLE_TOKEN_FILE.write_text(credentials.to_json())
    print("Google Drive authorization successful!")
