from openai import AsyncOpenAI
import openai
import os
import base64

# Сохраняем credentials.json из переменной окружения
creds_base64 = os.getenv("GOOGLE_CREDENTIALS_JSON")

if creds_base64:
    try:
        decoded = base64.b64decode(creds_base64).decode("utf-8")
        with open("credentials.json", "w") as f:
            f.write(decoded)
        print("✅ credentials.json успешно создан из base64.")
    except Exception as e:
        print(f"❌ Ошибка при создании credentials.json: {e}")
else:
    print("⚠️ Переменная окружения GOOGLE_CREDENTIALS_JSON не найдена.")


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
