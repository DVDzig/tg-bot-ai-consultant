import logging
from openai import AsyncOpenAI
from youtubesearchpython import VideosSearch

# --- Константы ---
OPENAI_API_KEY = "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"
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- Генерация ответа OpenAI ---
async def generate_openai_answer(question, prompt, chat_history=None):
    try:
        messages = [{"role": "system", "content": prompt}]
        if chat_history:
            messages += chat_history
        messages.append({"role": "user", "content": question})

        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        answer = response.choices[0].message.content.strip()
        return answer

    except Exception as e:
        logging.error(f"Ошибка при запросе к OpenAI: {e}")
        return "Произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."


# --- Поиск видео на YouTube ---

async def find_youtube_videos(query, max_results=3):
    try:
        search = VideosSearch(query, limit=max_results)
        results = await search.next()

        links = []
        for video in results["result"]:
            links.append(video["link"])

        return links

    except Exception as e:
        logging.error(f"Ошибка поиска YouTube: {e}")
        return []
