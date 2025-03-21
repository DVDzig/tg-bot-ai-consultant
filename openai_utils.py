import logging
from openai import AsyncOpenAI
import openai
from sheet_utils import df_structured

# --- Инициализация OpenAI ---
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- Генерация промптов по дисциплинам ---
def generate_discipline_prompts(df):
    prompts = {}
    for _, row in df.iterrows():
        discipline = row["Дисциплины"]
        module = row["Модуль"]

        if "физич" in module.lower():
            style = (
                f"Ты спортивный тренер и эксперт по дисциплине '{discipline}'. "
                "Дай четкий и мотивационный ответ, используй примеры из практики."
            )
        elif "медиа" in module.lower() or "журналист" in module.lower():
            style = (
                f"Ты медиаконсультант и специалист по дисциплине '{discipline}'. "
                "Отвечай кратко, ясно, используй примеры из медиа."
            )
        elif "истори" in module.lower() or "теори" in module.lower():
            style = (
                f"Ты научный эксперт по дисциплине '{discipline}'. "
                "Дай развернутый ответ с историческими примерами."
            )
        else:
            style = (
                f"Ты эксперт по дисциплине '{discipline}'. "
                "Отвечай по сути, помогай студенту разобраться."
            )

        prompts[discipline] = style

    return prompts

# --- Генерация словаря дисциплин с промптами ---
try:
    DISCIPLINE_PROMPTS = generate_discipline_prompts(df_structured)
except Exception as e:
    logging.error(f"[ERROR] Не удалось сгенерировать промпты: {e}")
    DISCIPLINE_PROMPTS = {}

# --- Экспортируем переменные для других файлов ---
__all__ = ["openai_client", "DISCIPLINE_PROMPTS"]
