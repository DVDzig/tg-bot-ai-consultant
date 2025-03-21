import logging
from datetime import datetime, timedelta
from aiogram import Dispatcher
from bot_handlers import setup_bot_handlers

def register_handlers(dp: Dispatcher):
    setup_bot_handlers(dp)


FREE_LIMIT_RESET_DAYS = {
    "Новичок": 2,
    "Продвинутый": 3,
    "Профи": 7,
    "Эксперт": 9999  # не ограничен
}

FREE_QUESTION_LIMITS = {
    "Новичок": 10,
    "Продвинутый": 20,
    "Профи": 30,
    "Эксперт": 99999  # не ограничен
}

XP_PER_QUESTION = 1

ADMIN_IDS = [150532949]  # Добавь нужные ID

# Прогресс бар
def generate_progress_bar(current, total, length=10):
    filled = int(current / total * length) if total else length
    empty = length - filled
    return "▓" * filled + "░" * empty

# Статус на основе XP
def get_status_from_xp(xp):
    if xp < 10:
        return "Новичок"
    elif xp < 50:
        return "Продвинутый"
    elif xp < 100:
        return "Профи"
    else:
        return "Эксперт"

# Статус и цели
def get_status_and_next_info(xp):
    if xp < 10:
        return "Новичок", "Продвинутый", 10
    elif xp < 50:
        return "Продвинутый", "Профи", 50
    elif xp < 100:
        return "Профи", "Эксперт", 100
    else:
        return "Эксперт", None, xp

# Проверка вопроса по ключам
def is_question_relevant(question, keywords):
    question_lower = question.lower()
    return any(kw in question_lower for kw in keywords)

# Обновление XP и статуса
def update_user_xp_and_status(record, user_sheet, row):
    try:
        xp = int(record.get("xp", 0)) if record.get("xp", "").strip() else 0
    except ValueError:
        xp = 0
    xp = int(record.get("xp", 0)) + XP_PER_QUESTION
    status = get_status_from_xp(xp)

    user_sheet.update_cell(row, record.keys().index("xp") + 1, xp)
    user_sheet.update_cell(row, record.keys().index("status") + 1, status)

# Проверка лимитов
def check_free_question_limit(record):
    status = record.get("status", "Новичок")
    try:
        xp = int(record.get("xp", 0)) if record.get("xp", "").strip() else 0
    except ValueError:
        xp = 0
    paid_questions = int(record.get("paid_questions", 0))
    last_reset_str = record.get("last_free_reset", "")

    free_limit = FREE_QUESTION_LIMITS.get(status, 0)
    reset_days = FREE_LIMIT_RESET_DAYS.get(status, 2)

    now = datetime.now()
    last_reset = datetime.strptime(last_reset_str, '%Y-%m-%d %H:%M:%S') if last_reset_str else now

    days_passed = (now - last_reset).days

    if days_passed >= reset_days:
        record["question_count"] = 0
        record["last_free_reset"] = now.strftime('%Y-%m-%d %H:%M:%S')
        return True, paid_questions > 0  # Сброс и проверка

    free_used = int(record.get("question_count", 0))

    if free_used < free_limit:
        return True, False  # Есть бесплатные

    return paid_questions > 0, paid_questions > 0  # Есть платные

# Списание платных вопросов
def deduct_paid_question(record, user_sheet, row):
    raw_value = record.get("paid_questions", "0")
    paid_questions = int(raw_value) if raw_value.strip().isdigit() else 0
    if paid_questions > 0:
        paid_questions -= 1
        user_sheet.update_cell(row, record.keys().index("paid_questions") + 1, paid_questions)

# Лидерборд
def build_leaderboard(user_data, mode="all"):
    now = datetime.now()
    leaderboard = []

    for record in user_data:
        if str(record.get("user_id")) in map(str, ADMIN_IDS):
            continue

        try:
            xp = int(record.get("xp", 0)) if record.get("xp", "").strip() else 0
        except ValueError:
            xp = 0
        last_active_str = record.get("last_interaction", "")

        try:
            last_active = datetime.strptime(last_active_str, '%Y-%m-%d %H:%M:%S')
        except:
            continue

        if mode == "week" and (now - last_active).days > 7:
            continue
        if mode == "day" and now.date() != last_active.date():
            continue

        leaderboard.append((record.get("username", "Без имени"), xp))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    return leaderboard[:10]

