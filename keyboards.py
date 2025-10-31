from telegram import ReplyKeyboardMarkup

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ["🕐 Установить будильник", "📊 Моя статистика"],
    ["🧩 Пример головоломки", "❓ Помощь"]
], resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)