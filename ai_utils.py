# ai_utils.py
import logging
from openai import AsyncOpenAI

# --- ИНИЦИАЛИЗАЦИЯ ---
OPENAI_API_KEY = "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"
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- ПОЛУЧЕНИЕ ОТВЕТА ОТ OPENAI ---
async def get_openai_answer(prompt: str, chat_history: list):
    try:
        messages = [
            {"role": "system", "content": prompt},
            *chat_history
        ]

        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        answer = response.choices[0].message.content.strip()
        return answer

    except Exception as e:
        logging.error(f"Ошибка OpenAI: {e}")
        return "⚠️ Произошла ошибка при получении ответа от ИИ. Попробуй позже."

# --- ФИЛЬТРАЦИЯ ПО ВОПРОСАМ ---
def is_question_relevant(question: str, keywords: list) -> bool:
    question_lower = question.lower()
    return any(kw in question_lower for kw in keywords)

# --- ПОСТРОЕНИЕ ПРОГРЕСС-БАРА ---
def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
    if total == 0:
        return "▓" * length  # Полный бар, если достигнута максимальная цель
    filled = int(current / total * length)
    empty = length - filled
    return "▓" * filled + "░" * empty

# --- ПОЛУЧЕНИЕ КЛЮЧЕЙ ДЛЯ ДИСЦИПЛИНЫ ---
def parse_keywords(raw_keywords: str) -> list:
    return [kw.strip().lower() for kw in raw_keywords.split(",") if kw.strip()]

async def generate_youtube_links(prompt_text, max_links=3):
    # Простой OpenAI-запрос для генерации ссылок
    query_prompt = (
        f"Подбери {max_links} полезных ссылок на YouTube, "
        f"связанных с темой: {prompt_text}. "
        f"Форматируй как список ссылок, без лишнего текста."
    )

    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": query_prompt}]
    )

    reply = response.choices[0].message.content.strip()
    return reply
