from google_sheets_utils import user_sheet
from config_utils import ADMIN_IDS
from datetime import datetime, timedelta

# --- Состояние пользователей (в памяти) ---
user_state = {}

# --- Загрузка данных пользователя из таблицы ---
def load_user_data():
    return user_sheet.get_all_records()

# --- Получение записи пользователя по user_id ---
def get_user_record(user_id):
    users = user_sheet.get_all_records()
    for i, user in enumerate(users, start=2):
        if str(user["user_id"]) == str(user_id):
            return user, i
    return None, None

# --- Обновление пользователя в таблице ---
def update_user_in_user_sheet(user_id, username, question_increment=True, discipline=None, module=None):
    record, row_number = get_user_record(user_id)
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    today_str = now.strftime('%Y-%m-%d')

    if record:
        # Безопасное преобразование
        def safe_int(value):
            try:
                return int(str(value).strip())
            except (ValueError, TypeError):
                return 0

        question_count = safe_int(record.get("question_count", 0))
        xp = safe_int(record.get("xp", 0))
        xp_today = safe_int(record.get("xp_today", 0))
        xp_week = safe_int(record.get("xp_week", 0))
        paid_questions = safe_int(record.get("paid_questions", 0))
        status = record.get("status", "Новичок")

        last_interaction_str = record.get("last_interaction", "")
        try:
            last_interaction = datetime.strptime(last_interaction_str, '%Y-%m-%d %H:%M:%S')
        except:
            last_interaction = now

        # Обнуление XP сегодня при новом дне
        if now.date() != last_interaction.date():
            xp_today = 0
            user_sheet.update_cell(row_number, 11, xp_today)

        # Обнуление XP за неделю при новом понедельнике
        if now.isocalendar()[1] != last_interaction.isocalendar()[1]:  # Неделя изменилась
            xp_week = 0
            user_sheet.update_cell(row_number, 12, xp_week)

        if question_increment:
            question_count += 1
            xp += 1
            xp_today += 1
            xp_week += 1

            user_sheet.update_cell(row_number, 5, question_count)
            user_sheet.update_cell(row_number, 10, xp)
            user_sheet.update_cell(row_number, 11, xp_today)
            user_sheet.update_cell(row_number, 12, xp_week)

        user_sheet.update_cell(row_number, 4, now_str)  # last_interaction

        if discipline:
            user_sheet.update_cell(row_number, 8, discipline)
        if module:
            user_sheet.update_cell(row_number, 9, module)

        if not record.get("first_interaction"):
            user_sheet.update_cell(row_number, 3, now_str)

    else:
        new_row = [
            user_id, username, now_str, now_str,
            1 if question_increment else 0, 0, "Новичок",
            discipline or "", module or "",
            1 if question_increment else 0,  # xp
            1 if question_increment else 0,  # xp_today
            1 if question_increment else 0,  # xp_week
            0,  # paid_questions
            now_str  # last_free_reset
        ]
        user_sheet.append_row(new_row)
