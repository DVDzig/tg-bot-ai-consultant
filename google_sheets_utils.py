import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
import os
from datetime import datetime
from config_utils import SHEET_ID, USER_SHEET_ID, LOGS_FOLDER_ID
import base64

# --- Подключение к Google API ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# --- Переменная окружения ---
encoded = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not encoded:
    print("❌ GOOGLE_CREDENTIALS_JSON не найдена.")
    exit(1)

try:
    # Расшифровка и создание credentials.json
    decoded = base64.b64decode(encoded).decode("utf-8")
    with open("credentials.json", "w") as f:
        f.write(decoded)
    print("✅ credentials.json успешно создан.")
except Exception as e:
    print(f"❌ Ошибка при создании credentials.json: {e}")

# Авторизация
try:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)
    print("✅ Авторизация прошла успешно.")
except Exception as e:
    print(f"❌ Ошибка авторизации: {e}")
    exit(1)

with open("credentials.json", "w") as f:
    f.write(decoded)


# Таблица с планом дисциплин
sheet = client.open_by_key(SHEET_ID).worksheet("План")

# Таблица с пользователями
user_sheet = client.open_by_key(USER_SHEET_ID).worksheet("Лист1")

# --- Работа с таблицами ---
def get_sheet_data(sheet_id: str, worksheet_name: str):
    try:
        worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return worksheet, data
    except Exception as e:
        logging.error(f"Ошибка получения данных таблицы: {e}")
        return None, []

# --- Загрузка логов на Google Диск ---
def upload_log_to_drive(discipline: str):
    try:
        file_path = f"logs/{discipline}.txt"
        if not os.path.exists(file_path):
            logging.warning(f"Файл {file_path} не найден для загрузки.")
            return

        file_metadata = {
            'name': f"{discipline}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt",
            'parents': [LOGS_FOLDER_ID]
        }

        media = MediaFileUpload(file_path, mimetype='text/plain')
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"Файл {file_path} успешно загружен на Google Диск.")

    except Exception as e:
        logging.error(f"Ошибка загрузки лога в Google Диск: {e}")

# --- Обновление ключевых слов в таблице ---
def update_keywords_in_sheet(sheet_id: str, worksheet_name: str, discipline: str, keywords: list):
    try:
        worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        data = worksheet.get_all_records()

        for i, row in enumerate(data):
            if row.get("Дисциплины", "").strip().lower() == discipline.strip().lower():
                keywords_str = ", ".join(keywords)
                worksheet.update_cell(i + 2, 7, keywords_str)  # Столбец G = 7
                logging.info(f"Ключевые слова обновлены для дисциплины '{discipline}'.")
                return

        logging.warning(f"Дисциплина '{discipline}' не найдена для обновления ключей.")

    except Exception as e:
        logging.error(f"Ошибка обновления ключевых слов: {e}")

# --- Получение строки пользователя в таблице ---
def get_user_record(user_id):
    try:
        records = user_sheet.get_all_records()
        for idx, record in enumerate(records):
            if str(record.get("user_id")) == str(user_id):
                return idx + 2, record  # +2, потому что данные начинаются со 2-й строки
        return None, None
    except Exception as e:
        logging.error(f"Ошибка получения записи пользователя: {e}")
        return None, None

def update_paid_questions(user_id, amount):
    row_number, record = get_user_record(user_id)
    if row_number and record:
        current_paid = int(record.get("paid_questions", 0)) if str(record.get("paid_questions", 0)).isdigit() else 0
        new_paid = current_paid + amount
        user_sheet.update_cell(row_number, get_column_index("paid_questions"), new_paid)

def get_column_index(column_name):
    headers = user_sheet.row_values(1)
    try:
        return headers.index(column_name) + 1
    except ValueError:
        return None
