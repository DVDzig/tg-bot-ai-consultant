from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
        [KeyboardButton(text=f"📚 Выбери дисциплину")],
        [KeyboardButton(text=f"👤 Личный кабинет")], [KeyboardButton(text=f"🏆 Лидерборд")]
        [KeyboardButton("💳 Купить вопросы")]
        ],
        resize_keyboard=True
    )
    
    

# Клавиатура для взаимодействия с ИИ
def ai_interaction_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧹 Новый вопрос"), KeyboardButton(text="🧩 Продолжить вопрос")],
            [KeyboardButton(text="🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )

# Клавиатура для выбора учебных материалов
def materials_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 Задать вопрос консультанту")],
            [KeyboardButton(text="🔙 Назад к дисциплинам")]
        ],
        resize_keyboard=True
    )

# Клавиатура для профиля
def profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )
