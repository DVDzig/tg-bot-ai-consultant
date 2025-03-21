from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
import logging
import os

# --- Константы для Google Drive ---
CREDENTIALS_FILE = "credentials.json"
LOGS_FOLDER_ID = "1BAJrLKRDleaBkMomaI1c4iYYVEclk-Ab"

# --- Авторизация ---
SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)

# --- Загрузка логов на Google Диск ---
def upload_log_to_drive(discipline_name: str):
    file_path = f"logs/{discipline_name}.txt"

    if not os.path.exists(file_path):
        logging.warning(f"Файл лога {file_path} не найден.")
        return

    file_metadata = {
        "name": f"{discipline_name}.txt",
        "parents": [LOGS_FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype="text/plain")

    try:
        # Проверка на наличие файла с таким именем
        response = drive_service.files().list(
            q=f"name='{discipline_name}.txt' and '{LOGS_FOLDER_ID}' in parents",
            spaces='drive',
            fields="files(id, name)",
            pageSize=1
        ).execute()

        files = response.get('files', [])

        if files:
            file_id = files[0]['id']
            drive_service.files().update(fileId=file_id, media_body=media).execute()
            logging.info(f"Файл {discipline_name}.txt обновлён на Google Диске.")
        else:
            drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            logging.info(f"Файл {discipline_name}.txt загружен на Google Диск.")

    except Exception as e:
        logging.error(f"Ошибка при загрузке лога на Google Диск: {e}")
