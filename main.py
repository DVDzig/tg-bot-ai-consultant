import os
import json
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties
from config_utils import TOKEN
from bot_utils import register_handlers

# --- 1. Создание credentials.json из переменной окружения ---
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

# --- 2. Логирование ---
logging.basicConfig(level=logging.INFO)

# --- 3. Основной запуск бота и сервера Webhook ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    register_handlers(dp)

    # Установка команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь")
    ], scope=BotCommandScopeDefault())

    # Настройка Webhook
    RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not RENDER_HOST:
        logging.error("❌ RENDER_EXTERNAL_HOSTNAME не задан")
        return
    WEBHOOK_PATH = f"/webhook/{TOKEN}"
    WEBHOOK_URL = f"https://{RENDER_HOST}{WEBHOOK_PATH}"

    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

    # Обработчик Webhook
    async def webhook_handler(request):
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response()

    # Запуск aiohttp сервера
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, webhook_handler)

    port = int(os.environ.get('PORT', 8000))
    print(f"🌐 Запуск сервера на порту {port}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    await site.start()

    logging.info("Бот запущен и слушает Webhook...")

    # Поддержка работы сервера
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
