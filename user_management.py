# user_management.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- Константы ---
CREDENTIALS_FILE = "credentials.json"
USER_SHEET_ID = "1Ialmy0K2HfIWQFYjYZP6bBFuRBoK_aHXDX6BZSPPM7k"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

user_sheet = client.open_by_key(USER_SHEET_ID).worksheet("Лист1")

# --- Работа с пользователями ---
def get_all_users():
    return user_sheet.get_all_records()

def find_user_by_id(user_id):
    users = get_all_users()
    for idx, user in enumerate(users):
        if str(user["user_id"]) == str(user_id):
            return user, idx + 2  # строка +2 (заголовок + 1)
    return None, None

def update_user_interaction(user_id):
    user, row = find_user_by_id(user_id)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if user:
        user_sheet.update_cell(row, 4, now)  # last_interaction

# --- Статус и XP ---
STATUS_TIERS = [
    ("Новичок", 10),
    ("Продвинутый", 50),
    ("Профи", 100),
    ("Эксперт", float("inf"))
]

FREE_LIMIT_DAYS = {
    "Новичок": 2,
    "Продвинутый": 3,
    "Профи": 7,
    "Эксперт": 0
}

def get_status_from_questions(q_count):
    for status, threshold in STATUS_TIERS:
        if q_count <= threshold:
            return status
    return "Эксперт"

def update_status_and_xp(user_id, increment_question=True):
    user, row = find_user_by_id(user_id)
    if not user:
        return

    q_count = int(user.get("question_count", 0))
    xp = int(user.get("xp", 0))

    if increment_question:
        q_count += 1
        xp += 5

    status = get_status_from_questions(q_count)

    user_sheet.update_cell(row, 5, q_count)  # question_count
    user_sheet.update_cell(row, 9, xp)       # xp
    user_sheet.update_cell(row, 7, status)   # status
    user_sheet.update_cell(row, 4, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # last_interaction
