from openai import AsyncOpenAI
import openai
import os

# Сохраняем credentials.json из переменной окружения
if os.getenv("GOOGLE_CREDS_JSON"):
    with open("credentials.json", "w") as f:
        f.write(os.getenv("GOOGLE_CREDS_JSON"))


# --- Константы ---
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
openai.api_key = OPENAI_API_KEY

CREDENTIALS_FILE = "credentials.json"
SHEET_ID = os.getenv("SHEET_ID")
USER_SHEET_ID = os.getenv("USER_SHEET_ID")
LOGS_FOLDER_ID = os.getenv("LOGS_FOLDER_ID")
ADMIN_IDS = ["150532949"]  # Подставь твой Telegram user_id

FREE_QUESTION_LIMITS = {
    "Новичок": 10,
    "Продвинутый": 20,
    "Профи": 30,
    "Эксперт": float('inf')
}
