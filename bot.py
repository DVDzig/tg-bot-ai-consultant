import logging
import asyncio
import pandas as pd
import gspread
import openai
import os
import json

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from openai import AsyncOpenAI
import base64

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


# Логирование
logging.basicConfig(level=logging.INFO)

# --- Константы ---
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
openai.api_key = OPENAI_API_KEY

CREDENTIALS_FILE = "credentials.json"
SHEET_ID = "1vwRZKDUWOAgjCmHd5Cea2lrGraCULkrW9G8BUlJzI0Q"
USER_SHEET_ID = "1Ialmy0K2HfIWQFYjYZP6bBFuRBoK_aHXDX6BZSPPM7k"
LOGS_FOLDER_ID = "1BAJrLKRDleaBkMomaI1c4iYYVEclk-Ab"

# Интервалы обновления бесплатных вопросов (в днях)
FREE_LIMIT_RESET_DAYS = {
    "Новичок": 2,
    "Продвинутый": 3,
    "Профи": 7,
    "Эксперт": None  # Экспертам не нужен лимит
}

# Авторизация Google API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
drive_service = build("drive", "v3", credentials=creds)

# Загрузка данных из Google Sheets
sheet = client.open_by_key(SHEET_ID).worksheet("План")
data = sheet.get_all_records(expected_headers=["Модуль", "Дисциплины", "Ключевые слова"])
df_structured = pd.DataFrame(data)

# Запуск бота
bot = Bot(token=TOKEN)
dp = Dispatcher()
user_state = {}

# Кэширование 
youtube_cache = {} # YouTube ссылок
cached_user_data = []  # Кэш пользовательских данных

# --- Функции клавиатур ---
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=f"📚 Выбери дисциплину")],
        [KeyboardButton(text=f"👤 Личный кабинет")], [KeyboardButton(text=f"🏆 Лидерборд")]
        [KeyboardButton("💳 Купить вопросы")]
    ],
    resize_keyboard=True
)

# --- Унификация генерации промптов ---
DISCIPLINE_PROMPTS = {
    # Пример
    "Психология": "Ты эксперт по психологии спорта. Отвечай строго по теме."
}

# Получение ключевых слов дисциплины
def get_keywords_for_discipline(discipline_name):
    try:
        # Поиск строки с нужной дисциплиной в датафрейме
        row = df_structured[df_structured["Дисциплины"].str.strip().str.lower() == discipline_name.strip().lower()]
        if not row.empty:
            keywords_str = row.iloc[0].get("Ключевые слова", "")
            if keywords_str:
                return [kw.strip().lower() for kw in keywords_str.split(",") if kw.strip()]
        return []
    except Exception as e:
        logging.error(f"Ошибка получения ключевых слов: {e}")
        return []
    
# --- Проверка вопроса по ключевым словам ---
def is_question_relevant(question, keywords):
    question_lower = question.lower()
    return any(kw in question_lower for kw in keywords)

# --- Генерация YouTube-ссылок ---
async def generate_youtube_links(question, count=1):
    try:
        prompt = (
            f"Предложи {count} ссылок на полезные видео YouTube по теме: '{question}'. "
            "Только ссылки, без описаний, на русском языке."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка генерации ссылок: {e}")
        return ""
    
async def generate_youtube_links_cached(question, count=1):
    if question in youtube_cache:
        return youtube_cache[question]

    links = await generate_youtube_links_cached(question, count)
    youtube_cache[question] = links
    return links


# Сначала определяем функцию
def generate_discipline_prompts(df):
    prompts = {}
    for _, row in df.iterrows():
        discipline = row["Дисциплины"]
        module = row["Модуль"]

        # Определим стиль по модулю
        if "физич" in module.lower():
            style = (
                "Ты спортивный тренер и эксперт по дисциплине "
                f"'{discipline}'. Дай четкий и мотивационный ответ, используй примеры из практики."
            )
        elif "медиа" in module.lower() or "журналист" in module.lower():
            style = (
                f"Ты медиаконсультант и специалист по дисциплине '{discipline}'. "
                "Отвечай кратко, ясно, используй примеры из новостных медиа и коммуникаций."
            )
        elif "истори" in module.lower() or "теори" in module.lower():
            style = (
                f"Ты научный эксперт по дисциплине '{discipline}'. "
                "Дай развернутый, академичный ответ с историческими примерами."
            )
        else:
            style = (
                f"Ты эксперт по дисциплине '{discipline}'. "
                "Отвечай понятно, по сути, помогай студенту разобраться в теме."
            )

        prompts[discipline] = style

    return prompts

# Потом вызываем функцию
DISCIPLINE_PROMPTS = generate_discipline_prompts(df_structured)
    
# Меню выбора пакета
@dp.message(F.text == "💳 Купить вопросы")
async def show_question_packages(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📦 10 вопросов — 50₽")],
            [KeyboardButton("📦 20 вопросов — 90₽")],
            [KeyboardButton("📦 50 вопросов — 200₽")],
            [KeyboardButton("🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выбери пакет вопросов:", reply_markup=menu_keyboard)

# Обработка выбранного пакета
@dp.message(F.text.startswith("📦 "))
async def handle_package_selection(message: types.Message):
    text = message.text

    # Параметры пакетов
    packages = {
        "📦 10 вопросов — 50₽": (10, 5000),
        "📦 20 вопросов — 90₽": (20, 9000),
        "📦 50 вопросов — 200₽": (50, 20000),
    }

    if text not in packages:
        await message.answer("Пакет не найден. Пожалуйста, выбери из меню.")
        return

    questions, price = packages[text]

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Покупка вопросов",
        description=f"{questions} вопросов для личного консультанта",
        payload=f"buy_{questions}_q",
        provider_token="381764678:TEST:17602",  # Замени на боевой токен
        currency="RUB",
        prices=[LabeledPrice(label=f"{questions} вопросов", amount=price)],
        start_parameter="buy_q"
    )

    # Сохраняем выбранный пакет
    user_state[message.from_user.id]["pending_purchase"] = questions


# Подтверждение оплаты
@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# Успешная оплата
@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    user_id = message.from_user.id
    amount_paid = message.successful_payment.total_amount // 100

    # Получаем пакет из состояния
    questions_bought = user_state.get(user_id, {}).get("pending_purchase", 10)

    update_paid_questions(user_id, questions_bought)

    await message.answer(
        f"✅ Оплата {amount_paid}₽ прошла успешно!\n"
        f"Начислено {questions_bought} вопросов консультанту.",
        reply_markup=menu_keyboard
    )

    # Очистим покупку
    if user_id not in user_state:
        user_state[user_id] = {}
    user_state[user_id]["pending_purchase"] = 0


    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"💸 Оплата от @{message.from_user.username} ({user_id}): {amount_paid}₽, {questions_bought} вопросов начислено."
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу: {e}")


# --- Приветствие ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    welcome_text = (
        "Привет 👋\n\n"
        "Я — твой личный помощник в подготовке к экзаменам.\n"
        "Выбери, что хочешь сделать:"
    )
    await message.answer(welcome_text, reply_markup=menu_keyboard)

@dp.message(Command("gen_keys"))
async def manual_generate_keywords(message: types.Message):
    await message.answer("Генерация ключевых слов начата...")
    await generate_keywords_for_disciplines()
    await message.answer("Ключевые слова обновлены.")

# --- Выбор модуля ---
async def choose_module(message: types.Message):
    modules = df_structured["Модуль"].unique()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"📦 {mod}")] for mod in modules] + [[KeyboardButton(text=f"🔙 Назад в главное меню")]],
        resize_keyboard=True
    )
    await message.answer("Выбери модуль:", reply_markup=keyboard)

# Индексы колонок для Google Sheets (проверь, что они совпадают с таблицей!)
xp_column = 10         # Колонка XP
xp_today_column = 11   # XP за сегодня
xp_week_column = 12    # XP за неделю
paid_questions_column = 13
last_free_reset_column = 14

# Админы (ID в виде строки)
ADMIN_IDS = ["150532949"]  # Добавь свой ID

# Открываем таблицу по ID
user_sheet = client.open_by_key("1Ialmy0K2HfIWQFYjYZP6bBFuRBoK_aHXDX6BZSPPM7k").worksheet("Лист1")

# Централизованная загрузка и обновление данных из Google Sheets
def load_user_data(force_reload=False):
    global cached_user_data
    if force_reload or not cached_user_data:
        cached_user_data = user_sheet.get_all_records()
    return cached_user_data


def update_user_field(row_number, column, value):
    update_user_field(row_number, column, value)

# --- Обработчик личного кабинета ---
def update_paid_questions(user_id, questions, record=None):
    if not record:
        user_data = load_user_data()
        headers = user_data[0].keys()
        paid_q_index = list(headers).index("paid_questions") + 1

        for i, record in enumerate(user_data):
            if str(record.get("user_id")) == str(user_id):
                current_paid_q = int(record.get("paid_questions", 0)) if str(record.get("paid_questions", 0)).isdigit() else 0
                new_total = current_paid_q + questions
                user_sheet.update_cell(i + 2, paid_q_index, new_total)
                return
    else:
        current_paid_q = int(record.get("paid_questions", 0)) if str(record.get("paid_questions", 0)).isdigit() else 0
        new_total = current_paid_q + questions
        row_number = user_data.index(record) + 2
        user_sheet.update_cell(row_number, paid_q_index, new_total)


# --- Статусы и прогресс ---
def get_status_from_questions(question_count):
    if question_count <= 10:
        return "Новичок"
    elif question_count <= 50:
        return "Продвинутый"
    elif question_count <= 100:
        return "Профи"
    else:
        return "Эксперт"

def get_status_and_next_info(question_count):
    if question_count <= 10:
        return "Новичок", "Продвинутый", 11
    elif question_count <= 50:
        return "Продвинутый", "Профи", 51
    elif question_count <= 100:
        return "Профи", "Эксперт", 101
    else:
        return "Эксперт", None, None  # Эксперт — финальный статус

def generate_progress_bar(current, total, length=10):
    if total is None:  # Эксперт, прогресса нет
        return "▓" * length
    filled = int(current / total * length)
    empty = length - filled
    return "▓" * filled + "░" * empty

# --- Личный кабинет с прогрессом ---
async def show_user_profile(message: types.Message):
    user_id = message.from_user.id
    user_data = load_user_data()

    for record in user_data:
        if str(record["user_id"]) == str(user_id):
            q_count = int(record['question_count']) if str(record['question_count']).isdigit() else 0

            if str(user_id) in ADMIN_IDS:
                status = "👑 Эксперт"
                next_status = None
                goal = None
            else:
                status, next_status, goal = get_status_and_next_info(q_count)

            progress_bar = generate_progress_bar(q_count, goal)

            profile_info = (
                f"👤 <b>Профиль:</b> {record['username']}\n"
                f"🏆 <b>Статус:</b> {record['status']}\n"
                f"📅 <b>Первая сессия:</b> {record['first_interaction']}\n"
                f"📅 <b>Последняя сессия:</b> {record['last_interaction']}\n"
                f"📊 <b>Задано вопросов консультанту:</b> {q_count}\n"
                f"💰 <b>Куплено вопросов:</b> {record.get('paid_questions', 0)}\n"  # ← Добавлено
            )


            if next_status:
                profile_info += (
                    f"🚀 <b>Прогресс до:</b> {next_status} — {q_count}/{goal} вопросов\n"
                    f"<code>{progress_bar}</code>"
                )
            else:
                profile_info += "👑 Вы достигли максимального статуса!"

            await message.answer(profile_info, parse_mode="HTML")
            return

    await message.answer("Профиль не найден.")
    
# --- Работа с таблицей пользователей ---

# Функция получения записи о пользователе
def get_user_record(user_id):
    user_data = load_user_data()
    for row in user_data:
        if str(row["user_id"]) == str(user_id):
            return row  # Найденная запись
    return None  # Не найден


# Функция обновления записи или добавления новой
def update_user_in_user_sheet(user_id, username, question_increment=False, discipline=None, module=None):
    load_user_data(force_reload=True)  # Обновим кэш
    user_data = load_user_data()
    row_number = None
    record = None

    # Ищем строку пользователя
    for idx, row in enumerate(user_data):
        if str(row["user_id"]) == str(user_id):
            row_number = idx + 2  # +2 для учёта заголовка
            record = row
            break

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if record:
        print(f"Пользователь найден: {record}")
        
        status = record.get("status", "Новичок")
                
        # Проверка необходимости сброса лимита
        last_reset_str = record.get("last_free_reset", "")
        reset_days = FREE_LIMIT_RESET_DAYS.get(status, 2)

        if reset_days and last_reset_str:
            try:
                last_reset_date = datetime.strptime(last_reset_str, '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - last_reset_date).days >= reset_days:
                    user_sheet.update_cell(row_number, 5, 0)  # Обнуляем question_count
                    user_sheet.update_cell(row_number, 14, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    logging.info(f"Сброс лимита вопросов для пользователя {user_id}")
            except Exception as e:
                logging.error(f"Ошибка сброса лимита вопросов: {e}")

        # --- Лимиты и оплата ---
        paid_questions_raw = record.get("paid_questions", 0)
        try:
            paid_questions = int(paid_questions_raw)
        except (ValueError, TypeError):
            paid_questions = 0

        q_count = int(record.get("question_count", 0))
        free_limit = FREE_QUESTION_LIMITS.get(status, 10)

        can_get_xp = False
        if str(user_id) in ADMIN_IDS:
            can_get_xp = True
        elif q_count < free_limit:
            can_get_xp = True
        elif paid_questions > 0:
            paid_questions -= 1
            user_sheet.update_cell(row_number, 13, paid_questions)  # paid_questions
            can_get_xp = True

        # Обновляем last_interaction
        user_sheet.update_cell(row_number, 4, now_str)

        if question_increment and can_get_xp:
            new_q_count = q_count + 1
            user_sheet.update_cell(row_number, 5, new_q_count)  # question_count

            xp = int(record.get("xp", 0))
            xp_today = int(record.get("xp_today", 0))
            xp_week = int(record.get("xp_week", 0))

            new_xp = xp + 1
            new_xp_today = xp_today + 1
            new_xp_week = xp_week + 1

            user_sheet.update_cell(row_number, 10, new_xp)
            user_sheet.update_cell(row_number, 11, new_xp_today)
            user_sheet.update_cell(row_number, 12, new_xp_week)

            # Статус
            if str(user_id) in ADMIN_IDS:
                new_status = "👑 Эксперт"
            else:
                new_status = get_status_from_questions(new_xp)
            if record.get("status") != new_status:
                user_sheet.update_cell(row_number, 7, new_status)

        # Обновляем дисциплину и модуль
        if discipline:
            user_sheet.update_cell(row_number, 8, discipline)
        if module:
            user_sheet.update_cell(row_number, 9, module)

    else:
        # Новый пользователь
        print("Пользователь не найден, создаю нового...")
        new_q_count = 1 if question_increment else 0
        initial_xp = new_q_count
        new_row = [
            user_id, username, now_str, now_str, new_q_count, 0,
            "👑 Эксперт" if str(user_id) in ADMIN_IDS else "🐣 Новичок",
            discipline or "", module or "",
            initial_xp, initial_xp, initial_xp, 0  # Добавляем paid_questions = 0
        ]
        new_row.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # last_free_reset
        user_sheet.append_row(new_row)

# Добавим лимиты по статусам
FREE_QUESTION_LIMITS = {
    "Новичок": 10,
    "Продвинутый": 20,
    "Профи": 30,
    "Эксперт": float('inf'),  # Безлимит
}

# --- Функция обновления XP/статуса при бездействии ---
def update_xp_and_status_decay(user_record, row_number):
    try:
        user_id = str(user_record["user_id"])
        xp = int(user_record.get("xp", 0))
        last_interaction_str = user_record.get("last_interaction", "")
        
        if not last_interaction_str:
            return  # Нет даты — пропускаем

        last_interaction = datetime.strptime(last_interaction_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        days_inactive = (now - last_interaction).days

        xp_decay = 0
        if 5 <= days_inactive < 15:
            xp_decay = 5
        elif days_inactive >= 15:
            xp_decay = 10

        if xp_decay > 0:
            new_xp = max(xp - xp_decay, 0)
            user_sheet.update_cell(row_number, 10, new_xp)  # Столбец XP
            logging.info(f"Пользователь {user_id} не активен {days_inactive} дней. XP уменьшен на {xp_decay}")

            # Обновляем статус
            new_status = get_status_from_questions(new_xp)
            user_sheet.update_cell(row_number, 7, new_status)  # Столбец Статус
            logging.info(f"Новый статус пользователя {user_id}: {new_status}")

    except Exception as e:
        logging.error(f"Ошибка при снижении XP для пользователя: {e}")

# Клавиатуры

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
        [KeyboardButton(text="🧩 Продолжить вопрос"), KeyboardButton(text="🧹 Новый вопрос")],
        [KeyboardButton(text="🔙 Назад в главное меню")]
    ],
    resize_keyboard=True
)

def profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад в главное меню")],
        ],
        resize_keyboard=True
    )

# ===== Работа с файлами логов =====
def ensure_local_log_dir():
    if not os.path.exists("logs"):
        os.makedirs("logs")

def get_local_log_path(discipline):
    return os.path.join("logs", f"{discipline}.json")

def load_log_local(discipline):
    ensure_local_log_dir()
    path = get_local_log_path(discipline)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_log_local(discipline, question, answer):
    logs = load_log_local(discipline)
    logs.append({"question": question, "answer": answer})
    path = get_local_log_path(discipline)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def search_log_for_answer(log_data, new_question):
    for entry in log_data:
        if new_question.lower() in entry["question"].lower():
            return entry["answer"]
    return None

def upload_log_to_drive(discipline):
    path = get_local_log_path(discipline)
    file_metadata = {
        "name": f"{discipline}_log.json",
        "parents": [LOGS_FOLDER_ID],
        "mimeType": "application/json"
    }

    # Удаляем старый файл, если есть
    query = f"'{LOGS_FOLDER_ID}' in parents and name = '{discipline}_log.json'"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    for file in results.get("files", []):
        drive_service.files().delete(fileId=file["id"]).execute()

    # Загружаем новый
    media = MediaFileUpload(path, mimetype="application/json")
    drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

# ====== ИИ Ответ ======
async def ask_ai_handler(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]["waiting_for_ai_question"] = True
    await message.answer("✍️ Напиши вопрос по дисциплине.")

    # Инициализация состояния пользователя
    if user_id not in user_state:
        user_state[user_id] = {}

    # --- ОБРАБОТКА КНОПОК ---
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    user_data = load_user_data()
    text = message.text 

    if text == "🔙 Назад в главное меню":
        user_state[user_id] = {}
        await message.answer("Вы в главном меню. Выберите действие:", reply_markup=menu_keyboard)
        return


    if text == "🔙 Назад к модулям":
        await choose_module(message)
        return

    if text == "🔙 Назад к дисциплинам":
        module_name = user_state.get(user_id, {}).get("module")
        if module_name:
            disciplines = df_structured[df_structured["Модуль"] == module_name]["Дисциплины"].unique()
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"📘 {discipline}")] for discipline in disciplines] + [[KeyboardButton(text="🔙 Назад к модулям")]],
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
                keyboard=[[KeyboardButton(text=f"📘 {discipline}")] for discipline in disciplines] + [[KeyboardButton(text="🔙 Назад к модулям")]],
                resize_keyboard=True
            )
            await message.answer(f"Выбери дисциплину в модуле '{module_name}':", reply_markup=keyboard)
        return

    if text.startswith("📘 "):  # Дисциплина
        discipline_name = text.replace("📘 ", "").strip()
        if discipline_name in df_structured["Дисциплины"].values:
            user_state[user_id]["discipline"] = discipline_name

            # Проверка правильности данных перед записью
            module_name = user_state[user_id].get("module")
            print(f"Пользователь {user_id}: дисциплина - {discipline_name}, модуль - {module_name}")
        
            # Обновляем дисциплину и модуль в таблице
            update_user_in_user_sheet(user_id, message.from_user.username, question_increment=False, discipline=discipline_name, module=module_name)
            load_user_data(force_reload=True)  # Обновим кэш

            await message.answer(f"Выбери действие по дисциплине '{discipline_name}':", reply_markup=materials_keyboard())
        else:
            await message.answer("Дисциплина не найдена. Пожалуйста, выбери из списка.")
        return

    if text == "💬 Личный консультант":
        await ask_ai_handler(message)
        return

    if text == "🧹 Новый вопрос":
        user_state[user_id]["chat_history"] = []
        await message.answer("Введите новый вопрос для ИИ:")
        return

    if text == "🧩 Продолжить вопрос":
        await message.answer("Продолжай задавать уточняющие вопросы:")
        return

# --- ЕСЛИ ОЖИДАЕМ ВОПРОС К ИИ С ФИЛЬТРОМ ---
    if user_state.get(user_id, {}).get("waiting_for_ai_question"):
        question = text
        discipline = user_state[user_id].get("discipline", "").strip()

        # Получение записи пользователя
        record = get_user_record(user_id)
        if not record:
            await message.answer("Ошибка профиля. Попробуйте снова.")
            return

        status = record.get("status", "Новичок")
        q_count = int(record.get("question_count", 0))
        paid_questions = int(record.get("paid_questions", 0))

        free_limit = FREE_QUESTION_LIMITS.get(status, 10)

    # Проверка лимита
    if str(user_id) not in ADMIN_IDS:
        if q_count >= free_limit and paid_questions <= 0:
            await message.answer("❗ Вы достигли лимита бесплатных вопросов.\n"
                                 "Купите дополнительные вопросы, чтобы продолжить.")
            return

        if not discipline:
            await message.answer("Пожалуйста, выбери дисциплину из списка 📚.")
            return

        # Получаем ключевые слова из таблицы
        keywords = get_keywords_for_discipline(discipline)
        if not keywords:
            await message.answer(f"Для дисциплины '{discipline}' ещё нет ключевых слов. Пожалуйста, выбери другую дисциплину.")
            return

        # Проверяем релевантность вопроса
        if not is_question_relevant(question, keywords):
            await message.answer(f"❗ Вопрос не относится к дисциплине '{discipline}'. Пожалуйста, выбери другую дисциплину из модуля 📚.")
            return

        # Продолжаем диалог с ИИ
        chat_history = user_state[user_id].get("chat_history", [])
        chat_history.append({"role": "user", "content": question})

        prompt = DISCIPLINE_PROMPTS.get(discipline, f"Ты эксперт в дисциплине '{discipline}'. Отвечай строго по теме дисциплины.")

        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}] + chat_history
        )

        ai_answer = response.choices[0].message.content.strip()
        chat_history.append({"role": "assistant", "content": ai_answer})
        
        # Определяем статус
        user_data = load_user_data()
        status = "Новичок"
        for record in user_data:
            if str(record["user_id"]) == str(user_id):
                status = record.get("status", "Новичок")
                break

        user_state[user_id]["chat_history"] = chat_history
        
        # Добавление видео по статусу с форматированием
        if status in ["Профи", "Эксперт"]:
            link_count = 1 if status == "Профи" else 3
            video_links = await generate_youtube_links(question, count=link_count)
            links_list = video_links.strip().split("\n")
            formatted_links = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links_list) if link.strip()])
            ai_answer += f"\n\n📹 <b>Рекомендуемые видео:</b>\n{formatted_links}"


        elif status == "Эксперт":
            video_links = await generate_youtube_links(question, count=3)
            links_list = video_links.strip().split("\n")
            formatted_links = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links_list) if link.strip()])
            ai_answer += f"\n\n📹 <b>Рекомендуемые видео:</b>\n{formatted_links}"

        await message.answer(f"💡 {ai_answer}")
        update_user_in_user_sheet(user_id, message.from_user.username, question_increment=True)
        load_user_data(force_reload=True)  # Обновим кэш
        await message.answer("Выбери следующее действие:", reply_markup=ai_interaction_keyboard)

        save_log_local(discipline, question, ai_answer)
        upload_log_to_drive(discipline)
        return

    if text == "🏅 Лидерборд":
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=f"🏆 Всё время"), KeyboardButton(text=f"📅 Неделя"), KeyboardButton(text=f"🗓 Сегодня")],
                [KeyboardButton(text=f"🔙 Назад в главное меню")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выбери зал славы:", reply_markup=keyboard)
        return

    if text in ["🏆 Всё время", "📅 Неделя", "🗓 Сегодня"]:
        user_data = load_user_data()

        # Получаем текущую дату
        now = datetime.now()

        leaderboard = []

        for user in user_data:
            # Пропускаем админов
            if str(user.get("user_id")) in ADMIN_IDS:
                continue

            xp = int(user.get("xp", 0))
            first_interaction_str = user.get("first_interaction", "")
            last_interaction_str = user.get("last_interaction", "")

            # Парсим даты
            try:
                first_interaction = datetime.strptime(first_interaction_str, '%Y-%m-%d %H:%M:%S')
                last_interaction = datetime.strptime(last_interaction_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue  # Пропускаем, если даты невалидные

            # Фильтрация по режиму
            if text == "📅 Неделя":
                if (now - last_interaction).days > 7:
                    continue
            elif text == "🗓 Сегодня":
                if (now.date() != last_interaction.date()):
                    continue

            leaderboard.append((user.get("username", "Без имени"), xp))

        # Сортировка по XP
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        if not leaderboard:
            await message.answer("Пока нет данных для отображения.")
            return

        # Формируем топ-10
        top_10 = leaderboard[:10]
        result_text = f"{text} – Топ 10\n\n"
        for idx, (username, xp) in enumerate(top_10, start=1):
            result_text += f"{idx}. {username}: {xp} XP\n"

        await message.answer(result_text)
        return

    # Игнорируем текст, если не ждем вопрос для ИИ
    if not user_state.get(user_id, {}).get("waiting_for_ai_question"):
        await message.answer("Пожалуйста, выбери опцию из меню.")

# Функция создания бота и Dispatcher
async def create_bot():
    return Bot(token=TOKEN)

# Асинхронная задача для проверки активности
async def check_user_activity():
    while True:
        user_data = load_user_data()
        for idx, record in enumerate(user_data):
            user_id = int(record["user_id"])
            if user_id == 150532949:  # Админ — пропуск
                continue

            last_interaction = datetime.strptime(record["last_interaction"], '%Y-%m-%d %H:%M:%S')
            days_since_last = (datetime.now() - last_interaction).days

            current_q_count = int(record["question_count"])
            adjusted_q_count = current_q_count

            if 5 <= days_since_last < 10:
                adjusted_q_count = max(0, current_q_count - 5)
            elif days_since_last >= 10:
                adjusted_q_count = max(0, current_q_count - 10)

            if adjusted_q_count != current_q_count:
                row_number = idx + 2
                user_sheet.update_cell(row_number, 5, adjusted_q_count)  # Обновим XP

                # Обновим статус
                new_status = get_status_from_questions(adjusted_q_count)
                if record["status"] != new_status:
                    user_sheet.update_cell(row_number, 7, new_status)

        await asyncio.sleep(86400)  # Проверка раз в сутки

# --- Генерация ключевых слов по дисциплинам ---
async def generate_keywords_for_disciplines():
    sheet = client.open_by_key(SHEET_ID).worksheet("План")
    data = sheet.get_all_records(expected_headers=["Модуль", "Дисциплины", "Лекции", "Презентации", "Тесты", "Практические задания", "Ключевые слова"])
    
    for idx, row in enumerate(data):
        if not row.get("Ключевые слова"):  # Генерировать только если пусто
            discipline = row["Дисциплины"]
            prompt = (
                f"Сгенерируй 50–70 ключевых слов и понятий, относящихся к дисциплине '{discipline}'. "
                "Перечисли их через запятую, без номеров и пояснений."
            )

            try:
                response = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                keywords = response.choices[0].message.content.strip()

                sheet.update_cell(idx + 2, 7, keywords)  # Обновляем колонку «Ключевые слова» (индекс 7)
                logging.info(f"Ключевые слова обновлены для '{discipline}'")
            except Exception as e:
                logging.error(f"Ошибка генерации ключей для '{discipline}': {e}", exc_info=True)

# Главная функция запуска
async def main():
    bot = await create_bot()
    dp = Dispatcher()

    logging.info("Бот успешно запущен! Ожидаю команды...")

    dp.message.register(send_welcome, F.text == "/start")
    dp.message.register(choose_module, F.text == "📚 Выбери дисциплину")
    dp.message.register(show_user_profile, F.text == "👤 Личный кабинет")
    dp.message.register(handle_all_messages)

    # Запускаем проверку активности фоном
    asyncio.create_task(check_user_activity())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
