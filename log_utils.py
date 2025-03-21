import logging
import os
import json
from gdrive_utils import upload_log_to_drive

# Создание папки logs
def ensure_local_log_dir():
    if not os.path.exists("logs"):
        os.makedirs("logs")

# Получение пути к файлу логов
def get_local_log_path(discipline):
    return os.path.join("logs", f"{discipline}.json")

# Загрузка логов
def load_log_local(discipline):
    ensure_local_log_dir()
    path = get_local_log_path(discipline)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Сохранение логов
def save_log_local(discipline, question, answer):
    try:
        logs = load_log_local(discipline)
        logs.append({"question": question, "answer": answer})
        filepath = get_local_log_path(discipline)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"[ERROR] Failed to save log locally: {e}")

# Поиск ответа в логах
def search_log_for_answer(log_data, new_question):
    for log_entry in log_data:
        if new_question.lower() in log_entry["question"].lower():
            return log_entry["answer"]
    return None

def upload_log_to_drive(discipline):
    try:
        filepath = get_local_log_path(discipline)
        if os.path.exists(filepath):
            upload_log_to_drive(filepath)
            logging.info(f"[UPLOAD] Log for '{discipline}' uploaded.")
    except Exception as e:
        logging.error(f"[ERROR] Failed to upload log to Drive: {e}")