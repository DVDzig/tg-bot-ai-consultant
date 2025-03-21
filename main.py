import os
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties

# --- 1. Создание credentials.json на Render ---
creds_str = os.getenv("GOOGLE_CREDENTIALS_JSON")

if creds_str:
    try:
        creds_dict = json.loads(creds_str)
        with open("credentials.json", "w") as f:
            json.dump(creds_dict, f)
        print("✅ credentials.json успешно создан из переменной окружения.")
    except Exception as e:
        print(f"❌ Ошибка при создании credentials.json: {e}")
else:
    print("⚠️ Переменная окружения GOOGLE_CREDENTIALS_JSON не найдена.")

# --- 2. Подключение констант и хендлеров ---
from config_utils import TOKEN
from bot_utils import register_handlers

# --- 3. Логирование ---
logging.basicConfig(level=logging.INFO)

# --- 4. Основной запуск бота ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    register_handlers(dp)

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь")
    ], scope=BotCommandScopeDefault())

    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
