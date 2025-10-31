import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from database import Database
from puzzles import get_random_puzzle, validate_answer
from keyboards import MAIN_KEYBOARD
from config import logger

# Инициализация базы данных
db = Database()

# Временное хранилище для примеров головоломок
user_example_puzzles = {}

def generate_random_wake_time(start_str: str, end_str: str) -> str:
    """Генерирует случайное время между start и end"""
    start = datetime.strptime(start_str, "%H:%M")
    end = datetime.strptime(end_str, "%H:%M")

    # Разница в минутах
    total_minutes = int((end - start).total_seconds() / 60)
    random_minutes = random.randint(0, total_minutes)

    wake_time = start + timedelta(minutes=random_minutes)
    return wake_time.strftime("%H:%M")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.save_user(user.id, user.first_name, user.username)

    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот 'Доброе утро' - умный будильник с головоломками!",
        reply_markup=MAIN_KEYBOARD
    )

async def set_alarm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало установки будильника"""
    await update.message.reply_text(
        "⏰ Введи время будильника в формате:\n\n"
        "ЧЧ:ММ - ЧЧ:ММ\n\n"
        "Например: 7:00 - 7:30\n"
        "Я разбужу тебя случайным временем в этом интервале"
    )

async def handle_alarm_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка установки будильника"""
    try:
        text = update.message.text
        if " - " not in text:
            raise ValueError

        start_str, end_str = text.split(" - ")
        user_id = update.effective_user.id

        # Проверяем формат времени
        datetime.strptime(start_str.strip(), "%H:%M")
        datetime.strptime(end_str.strip(), "%H:%M")

        db.set_alarm(user_id, start_str.strip(), end_str.strip())

        await update.message.reply_text(
            f"✅ Будильник установлен на интервал {start_str} - {end_str}\nПриятных снов! 🌙",
            reply_markup=MAIN_KEYBOARD
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Введи в формате: ЧЧ:ММ - ЧЧ:ММ\nНапример: 7:00 - 7:30"
        )

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя"""
    user_id = update.effective_user.id
    success, failed_first, failed_second = db.get_statistics(user_id)

    text = (
        f"📊 Твоя статистика за последние 7 дней:\n\n"
        f"✅ Успешных подъемов: {success}\n"
        f"❌ Не решил первую: {failed_first}\n"
        f"❌ Не решил вторую: {failed_second}\n\n"
        f"Продолжай в том же духе! 💪"
    )

    await update.message.reply_text(text)

async def show_example_puzzle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать пример головоломки"""
    puzzle = get_random_puzzle()
    user_id = update.effective_user.id

    # Сохраняем пример головоломки во временный словарь
    user_example_puzzles[user_id] = {
        'question': puzzle['question'],
        'answer': puzzle['answer']
    }

    await update.message.reply_text(
        f"🧩 Пример головоломки:\n\n{puzzle['question']}\n\n"
        f"Попробуй решить! Напиши ответ прямо здесь:"
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""
    help_text = (
        "🤖 Я - умный будильник 'Доброе утро'!\n\n"
        "Как это работает:\n"
        "1. Установи интервал пробуждения (например 7:00-7:30)\n"
        "2. Я разбужу тебя случайным временем в этом интервале\n"
        "3. Реши первую головоломку за 10 минут\n"
        "4. Через 10 минут реши вторую головоломку за 7 минут\n"
        "5. Получи статус 'Успешный подъем'! ✅\n\n"
        "Начни с кнопки 'Установить будильник'!"
    )
    await update.message.reply_text(help_text)

async def handle_puzzle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: dict):
    """Обработка ответа на головоломку"""
    user_id = update.effective_user.id
    user_answer = update.message.text.strip()

    # Проверяем ответ
    if validate_answer(user_answer, user_state['current_puzzle_answer']):
        if user_state['state'] == 'AWAITING_FIRST_PUZZLE':
            db.set_user_state(user_id, 'AWAITING_SECOND_PUZZLE')
            await update.message.reply_text("✅ Верно! Жди вторую головоломку через 10 минут!")

            # Запускаем вторую головоломку через 10 минут
            asyncio.create_task(send_delayed_second_puzzle(user_id, context))

        else:  # AWAITING_SECOND_RESPONSE
            db.set_user_state(user_id, 'SLEEP')
            db.add_statistics(user_id, 'success')
            await update.message.reply_text("🎉 Поздравляю! Ты официально проснулся! Хорошего дня! 🌞",
                                            reply_markup=MAIN_KEYBOARD)
    else:
        await update.message.reply_text("❌ Неверно! Попробуй еще раз:")

async def handle_example_puzzle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа на пример головоломки"""
    user_id = update.effective_user.id
    user_answer = update.message.text.strip()
    puzzle_data = user_example_puzzles.get(user_id)

    if not puzzle_data:
        await update.message.reply_text("Ошибка: головоломка не найдена")
        return

    # Проверяем ответ
    if validate_answer(user_answer, puzzle_data['answer']):
        await update.message.reply_text(
            "✅ Верно! Так я буду будить тебя каждое утро!",
            reply_markup=MAIN_KEYBOARD
        )
    else:
        await update.message.reply_text(
            f"❌ Неверно! Правильный ответ: {puzzle_data['answer']}\n\n"
            f"Попробуй другие примеры через кнопку '🧩 Пример головоломки'",
            reply_markup=MAIN_KEYBOARD
        )

    # Удаляем пример из временного хранилища
    if user_id in user_example_puzzles:
        del user_example_puzzles[user_id]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик сообщений"""
    text = update.message.text
    user_id = update.effective_user.id

    # Сначала проверяем состояние пользователя (решает головоломку)
    user_state = db.get_user_state(user_id)
    if user_state and user_state['state'] in ['AWAITING_FIRST_PUZZLE', 'AWAITING_SECOND_RESPONSE']:
        await handle_puzzle_answer(update, context, user_state)
        return

    # Потом проверяем, есть ли активный пример головоломки
    if user_id in user_example_puzzles:
        await handle_example_puzzle_answer(update, context)
        return

    # Потом проверяем команды с кнопок
    if text == "🕐 Установить будильник":
        await set_alarm_start(update, context)
    elif text == "📊 Моя статистика":
        await show_statistics(update, context)
    elif text == "🧩 Пример головоломки":
        await show_example_puzzle(update, context)
    elif text == "❓ Помощь":
        await show_help(update, context)
    elif " - " in text:
        # Только если есть дефис - пробуем установить будильник
        await handle_alarm_setup(update, context)
    else:
        # Любой другой текст - просто подсказка
        await update.message.reply_text(
            "Используй кнопки меню 👆\nИли введи время будильника в формате: 7:00 - 7:30",
            reply_markup=MAIN_KEYBOARD
        )

async def send_puzzle_to_user(user_id: int, context: ContextTypes.DEFAULT_TYPE, is_second=False):
    """Отправить головоломку пользователю"""
    puzzle = get_random_puzzle()

    db.set_user_state(
        user_id,
        'AWAITING_SECOND_RESPONSE' if is_second else 'AWAITING_FIRST_PUZZLE',
        puzzle['question'],
        puzzle['answer']
    )

    message_text = (
        f"Тук-тук! 🚪\nТы проснулся точно???\nДокажи! Реши:\n\n{puzzle['question']}"
        if is_second else
        f"Доброе утро! ☀️\nПора просыпаться! Реши головоломку:\n\n{puzzle['question']}"
    )

    await context.bot.send_message(user_id, message_text)

    # Запускаем таймер
    from config import FIRST_PUZZLE_TIMEOUT, SECOND_PUZZLE_TIMEOUT
    timeout = SECOND_PUZZLE_TIMEOUT if is_second else FIRST_PUZZLE_TIMEOUT
    asyncio.create_task(puzzle_timeout(user_id, context, is_second, timeout))

async def puzzle_timeout(user_id: int, context: ContextTypes.DEFAULT_TYPE, is_second: bool, timeout: int):
    """Таймаут для головоломки"""
    await asyncio.sleep(timeout)

    user_state = db.get_user_state(user_id)
    if user_state and user_state['state'] == ('AWAITING_SECOND_RESPONSE' if is_second else 'AWAITING_FIRST_PUZZLE'):
        status = 'failed_second' if is_second else 'failed_first'
        db.add_statistics(user_id, status)
        db.set_user_state(user_id, 'SLEEP')

        message = (
            "Время вышло! Подъем не подтвержден 😔"
            if is_second else
            "Время вышло! Сегодня не получилось проснуться вовремя 😔"
        )
        await context.bot.send_message(user_id, message, reply_markup=MAIN_KEYBOARD)

async def send_delayed_second_puzzle(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправить вторую головоломку через 10 минут"""
    from config import DELAY_BETWEEN_PUZZLES
    await asyncio.sleep(DELAY_BETWEEN_PUZZLES)
    await send_puzzle_to_user(user_id, context, is_second=True)