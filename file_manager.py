import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime
from config_utils import drive_service, LOGS_FOLDER_ID


def save_log_local(discipline, question, answer):
    date_str = datetime.now().strftime('%Y-%m-%d')
    log_folder = os.path.join("logs", discipline)
    os.makedirs(log_folder, exist_ok=True)
    file_path = os.path.join(log_folder, f"{date_str}.txt")

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]:\n")
        file.write(f"Q: {question}\n")
        file.write(f"A: {answer}\n\n")


def upload_log_to_drive(discipline):
    date_str = datetime.now().strftime('%Y-%m-%d')
    local_file = os.path.join("logs", discipline, f"{date_str}.txt")

    if not os.path.exists(local_file):
        return

    file_metadata = {
        'name': f"{discipline}_{date_str}.txt",
        'parents': [LOGS_FOLDER_ID]
    }
    media = MediaFileUpload(local_file, mimetype='text/plain')

    try:
        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
    except Exception as e:
        print(f"Ошибка загрузки в Google Drive: {e}")
