from openai import AsyncOpenAI
import openai

# --- Константы ---
TOKEN = "7136074525:AAFECZhYb27cppiFWvjNdnshAZ2KvoIPVyo"
OPENAI_API_KEY = "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"

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
openai.api_key = OPENAI_API_KEY

CREDENTIALS_FILE = "credentials.json"
SHEET_ID = "1vwRZKDUWOAgjCmHd5Cea2lrGraCULkrW9G8BUlJzI0Q"
USER_SHEET_ID = "1Ialmy0K2HfIWQFYjYZP6bBFuRBoK_aHXDX6BZSPPM7k"
LOGS_FOLDER_ID = "1BAJrLKRDleaBkMomaI1c4iYYVEclk-Ab"
ADMIN_IDS = ["150532949"]  # Подставь твой Telegram user_id

FREE_QUESTION_LIMITS = {
    "Новичок": 10,
    "Продвинутый": 20,
    "Профи": 30,
    "Эксперт": float('inf')
}
