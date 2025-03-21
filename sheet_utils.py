import gspread
from google.oauth2.service_account import Credentials
import logging
import pandas as pd

# --- Google Sheets Авторизация ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDENTIALS_FILE = "credentials.json"
SHEET_ID = "1vwRZKDUWOAgjCmHd5Cea2lrGraCULkrW9G8BUlJzI0Q"
USER_SHEET_ID = "1Ialmy0K2HfIWQFYjYZP6bBFuRBoK_aHXDX6BZSPPM7k"

creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# --- Загрузка данных ---
try:
    plan_sheet = client.open_by_key(SHEET_ID).worksheet("План")
    user_sheet = client.open_by_key(USER_SHEET_ID).worksheet("Лист1")

    plan_data = plan_sheet.get_all_records(expected_headers=[
        "Модуль", "Дисциплины", "Ключевые слова"
    ])

    user_data = user_sheet.get_all_records(expected_headers=[
        "user_id", "username", "first_interaction", "last_interaction",
        "question_count", "day_count", "status", "discipline", "module",
        "paid_questions", "xp", "last_free_reset"
    ])

except Exception as e:
    logging.error(f"Ошибка загрузки данных из Google Sheets: {e}")
    plan_data, user_data = [], []

# --- DataFrame по дисциплинам ---
df_structured = pd.DataFrame(plan_data)

# --- Получение ключевых слов дисциплины ---
def get_keywords_for_discipline(discipline_name):
    try:
        row = df_structured[df_structured["Дисциплины"] == discipline_name]
        if not row.empty:
            keywords_str = row.iloc[0].get("Ключевые слова", "")
            return [kw.strip().lower() for kw in keywords_str.split(",") if kw.strip()]
        return []
    except Exception as e:
        print(f"Ошибка получения ключевых слов: {e}")
        return []

# --- Получение строки пользователя ---
def get_user_record(user_id):
    for idx, record in enumerate(user_data):
        if str(record["user_id"]) == str(user_id):
            return idx + 2, record  # +2 потому что данные начинаются со 2-й строки
    return None, None

# --- Обновление данных таблиц ---
def refresh_plan_data():
    global plan_data
    plan_data = plan_sheet.get_all_records(expected_headers=[
        "Модуль", "Дисциплины", "Ключевые слова"
    ])

def refresh_user_data():
    global user_data
    user_data = user_sheet.get_all_records(expected_headers=[
        "user_id", "username", "first_interaction", "last_interaction",
        "question_count", "day_count", "status", "discipline", "module",
        "paid_questions", "xp", "last_free_reset"
    ])

# --- Экспортируемые переменные и функции ---
__all__ = [
    "df_structured", "get_keywords_for_discipline", "get_user_record",
    "refresh_plan_data", "refresh_user_data", "plan_sheet", "user_sheet",
    "plan_data", "user_data"
]
