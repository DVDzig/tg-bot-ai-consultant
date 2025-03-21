# --- main.py ---
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties

from config_utils import TOKEN
from bot_utils import register_handlers

# Логирование
logging.basicConfig(level=logging.INFO)

# --- Основной запуск бота ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Регистрация всех обработчиков
    register_handlers(dp)

    # Команды бота (по желанию)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь")
    ], scope=BotCommandScopeDefault())


    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
