import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import logging

# --- Константы ---
CREDENTIALS_FILE = "credentials.json"
USER_SHEET_ID = "1Ialmy0K2HfIWQFYjYZP6bBFuRBoK_aHXDX6BZSPPM7k"

# Авторизация Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
user_sheet = client.open_by_key(USER_SHEET_ID).worksheet("Лист1")

# Получение всех пользователей
def get_all_users():
    try:
        return user_sheet.get_all_records()
    except Exception as e:
        logging.error(f"Ошибка получения данных пользователей: {e}")
        return []

# Обновление данных пользователя
def update_user(user_id, **kwargs):
    try:
        records = get_all_users()
        for i, record in enumerate(records):
            if str(record.get("user_id")) == str(user_id):
                row_number = i + 2  # первая строка — заголовки
                for key, value in kwargs.items():
                    try:
                        col_number = record.keys().index(key) + 1
                        user_sheet.update_cell(row_number, col_number, value)
                    except Exception as e:
                        logging.warning(f"Ошибка обновления {key}: {e}")
                return
    except Exception as e:
        logging.error(f"Ошибка обновления пользователя {user_id}: {e}")

# Добавление нового пользователя
def add_new_user(user_id, username):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        user_sheet.append_row([
            user_id, username, now, now, 0, 0, "Новичок", "", "", 0, now  # включая paid_questions, last_free_reset
        ])
    except Exception as e:
        logging.error(f"Ошибка добавления нового пользователя {user_id}: {e}")

# Получение записи пользователя
def get_user_record(user_id):
    records = get_all_users()
    for record in records:
        if str(record.get("user_id")) == str(user_id):
            return record
    return None

# Проверка лимита бесплатных вопросов
def can_ask_free_question(user_record, free_limit):
    q_count = int(user_record.get("question_count", 0))
    paid = int(user_record.get("paid_questions", 0))
    if q_count < free_limit + paid:
        return True
    return False

# Списание вопроса и обновление времени
def spend_question(user_id):
    record = get_user_record(user_id)
    if not record:
        return False

    paid = int(record.get("paid_questions", 0))
    if paid > 0:
        update_user(user_id, paid_questions=paid - 1)
    else:
        q_count = int(record.get("question_count", 0)) + 1
        update_user(user_id, question_count=q_count)

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    update_user(user_id, last_interaction=now_str)
    return True
