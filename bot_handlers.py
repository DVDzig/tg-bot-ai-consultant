from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery
from config_utils import ADMIN_IDS
from ai_utils import generate_youtube_links
from user_utils import user_state, load_user_data, update_user_in_user_sheet, get_user_record
from sheet_utils import df_structured, get_keywords_for_discipline
from config_utils import FREE_QUESTION_LIMITS
from google_sheets_utils import update_paid_questions
from log_utils import save_log_local, upload_log_to_drive
from openai_utils import openai_client, DISCIPLINE_PROMPTS
from gdrive_utils import LOGS_FOLDER_ID

import logging
from datetime import datetime

# --- Клавиатуры ---
def materials_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"💬 Личный консультант")],
            [KeyboardButton(text=f"🔙 Назад к дисциплинам")]
        ],
        resize_keyboard=True
    )

ai_interaction_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=f"🧩 Продолжить вопрос"), KeyboardButton(text=f"🧹 Новый вопрос")],
        [KeyboardButton(text=f"🔙 Назад в главное меню")]
    ],
    resize_keyboard=True
)

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=f"📚 Выбери дисциплину")],
        [KeyboardButton(text=f"👤 Личный кабинет"), KeyboardButton(text=f"🏆 Лидерборд")],
        [KeyboardButton(text=f"💳 Купить вопросы")]
    ],
    resize_keyboard=True
)

# --- Команды и навигация ---
async def send_welcome(message: types.Message):
    welcome_text = (
        "Привет 👋\n\n"
        "Я — твой личный помощник в подготовке к экзаменам.\n"
        "Выбери, что хочешь сделать:"
    )
    await message.answer(welcome_text, reply_markup=menu_keyboard)

async def choose_module(message: types.Message):
    modules = df_structured["Модуль"].unique()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"📦 {mod}")] for mod in modules] + [[KeyboardButton(text="🔙 Назад в главное меню")]],
        resize_keyboard=True
    )
    await message.answer("Выбери модуль:", reply_markup=keyboard)

# --- Обработка сообщений ---
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    user_data = load_user_data()

    if text == "🔙 Назад в главное меню":
        user_state[user_id] = {}
        await message.answer("Вы в главном меню. Выберите действие:", reply_markup=menu_keyboard)
        return

    if text == "📚 Выбери дисциплину":
        await choose_module(message)
        return

    if text == "🔙 Назад к модулям":
        await choose_module(message)
        return

    if text == "🔙 Назад к дисциплинам":
        module_name = user_state.get(user_id, {}).get("module")
        if module_name:
            disciplines = df_structured[df_structured["Модуль"] == module_name]["Дисциплины"].unique()
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"📘 {d}")] for d in disciplines] + [[KeyboardButton(text=f"🔙 Назад к модулям")]],
                resize_keyboard=True
            )
            await message.answer(f"Выбери дисциплину в модуле '{module_name}':", reply_markup=keyboard)
        else:
            await choose_module(message)
        return

    if text.startswith("📦 "):  # Модуль
        module_name = text.replace("📦 ", "").strip()
        if module_name in df_structured["Модуль"].values:
            user_state[user_id] = {"module": module_name}
            disciplines = df_structured[df_structured["Модуль"] == module_name]["Дисциплины"].unique()
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"📘 {d}")] for d in disciplines] + [[KeyboardButton(text=f"🔙 Назад к модулям")]],
                resize_keyboard=True
            )
            await message.answer(f"Выбери дисциплину в модуле '{module_name}':", reply_markup=keyboard)
        return

    if text.startswith("📘 "):  # Дисциплина
        discipline_name = text.replace("📘 ", "").strip()
        if discipline_name in df_structured["Дисциплины"].values:
            user_state[user_id]["discipline"] = discipline_name
            module_name = user_state[user_id].get("module")
            update_user_in_user_sheet(user_id, message.from_user.username, question_increment=False, discipline=discipline_name, module=module_name)
            await message.answer(f"Выбери действие по дисциплине '{discipline_name}':", reply_markup=materials_keyboard())
        else:
            await message.answer("Дисциплина не найдена.")
        return

    if text == "💬 Личный консультант":
        user_state[user_id]["waiting_for_ai_question"] = True
        await message.answer("✍️ Напиши вопрос по дисциплине.")
        return

    if text == "🧹 Новый вопрос":
        user_state[user_id]["chat_history"] = []
        await message.answer("Введите новый вопрос для ИИ:")
        return

    if text == "🧩 Продолжить вопрос":
        await message.answer("Продолжай задавать уточняющие вопросы:")
        return

    # --- Работа с ИИ ---
    if user_state.get(user_id, {}).get("waiting_for_ai_question"):
        await process_ai_question(message)
        return

    await message.answer("Пожалуйста, выбери опцию из меню.")

# --- Ответ ИИ ---
async def process_ai_question(message: types.Message):
    user_id = message.from_user.id
    question = message.text
    discipline = user_state[user_id].get("discipline", "")
    if not discipline:
        await message.answer("Выберите дисциплину из списка.")
        return

    record, row_number = get_user_record(user_id)
    if not record:
        await message.answer("Ошибка профиля.")
        return

    try:
        status = record.get("status", "Новичок")
        q_count = int(record.get("question_count", 0) or 0)
        raw_value = record.get("paid_questions", "0")
        paid_questions = int(raw_value) if raw_value.strip().isdigit() else 0
    except Exception as e:
        await message.answer("Ошибка данных профиля.")
        logging.error(f"Ошибка при обработке данных пользователя: {e}")
        return

    free_limit = FREE_QUESTION_LIMITS.get(status, 10)

    if str(user_id) not in ADMIN_IDS and q_count >= free_limit and paid_questions <= 0:
        await message.answer("❗ Лимит бесплатных вопросов исчерпан. Купите дополнительные вопросы.")
        return

    keywords = get_keywords_for_discipline(discipline)
    if not any(kw in question.lower() for kw in keywords):
        await message.answer(f"❗ Вопрос не относится к дисциплине '{discipline}'. Выберите другую.")
        return

    chat_history = user_state[user_id].get("chat_history", [])
    chat_history.append({"role": "user", "content": question})

    prompt = DISCIPLINE_PROMPTS.get(discipline, f"Ты эксперт в дисциплине '{discipline}'. Отвечай строго по теме.")
    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}] + chat_history
    )

    ai_answer = response.choices[0].message.content.strip()
    chat_history.append({"role": "assistant", "content": ai_answer})
    user_state[user_id]["chat_history"] = chat_history

    if status in ["Профи", "Эксперт"]:
        link_count = 1 if status == "Профи" else 3
        video_links = await generate_youtube_links(question, link_count)
        links_list = video_links.strip().split("\n")
        formatted_links = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links_list) if link.strip()])
        ai_answer += f"\n\n📹 <b>Рекомендуемые видео:</b>\n{formatted_links}"

    await message.answer(f"💡 {ai_answer}", parse_mode="HTML")
    update_user_in_user_sheet(user_id, message.from_user.username, question_increment=True)
    await message.answer("Выбери следующее действие:", reply_markup=ai_interaction_keyboard)

    save_log_local(discipline, question, ai_answer)
    upload_log_to_drive(discipline)

# --- Регистрация всех хендлеров ---
def setup_bot_handlers(router: Router):
    router.message.register(send_welcome, Command("start"))
    router.message.register(handle_all_messages)
