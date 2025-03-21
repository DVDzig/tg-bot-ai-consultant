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

# --- 4. Основной запуск бота и Webhook ---
from aiohttp import web
from aiogram import types

# Глобально объявляем переменные
bot = None
dp = None

async def main():
    global bot, dp
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    register_handlers(dp)

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь")
    ], scope=BotCommandScopeDefault())

    logging.info("Бот запущен!")

    # --- Установка Webhook ---
    RENDER_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    WEBHOOK_PATH = f"/webhook/{TOKEN}"
    WEBHOOK_URL = f"https://{RENDER_HOSTNAME}{WEBHOOK_PATH}"

    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

    # --- Запуск сервера ---
    app = web.Application()
    
    async def webhook_handler(request):
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response()

    app.router.add_post(WEBHOOK_PATH, webhook_handler)

    port = int(os.environ.get('PORT', 8000))
    print(f"🌐 Запуск сервера на порту {port}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Ожидаем завершения
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
