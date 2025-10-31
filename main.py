import asyncio
from datetime import time
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, logger
from handlers import (
    start, handle_message,
    send_puzzle_to_user, generate_random_wake_time,
    db
)
from database import Database

async def check_alarms(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет и активирует будильники каждую минуту"""
    alarms = db.get_active_alarms()

    current_time = datetime.now()
    current_date = current_time.date().isoformat()
    current_time_str = current_time.strftime("%H:%M")

    for user_id, time_start_str, time_end_str, random_wake_time, last_activation_date in alarms:
        # Если нет случайного времени ИЛИ сегодня еще не активировался
        if not random_wake_time or last_activation_date != current_date:
            # Генерируем случайное время
            wake_time = generate_random_wake_time(time_start_str, time_end_str)

            # Сохраняем в базу
            db.update_alarm_wake_time(user_id, wake_time, current_date)
            logger.info(f"Сгенерировано время пробуждения для {user_id}: {wake_time}")
            continue

        # Проверяем, пора ли будить
        if random_wake_time == current_time_str:
            # ЗВОНИМ БУДИЛЬНИК!
            await context.bot.send_message(user_id, "🔔 🔔 🔔 БУДИЛЬНИК! 🔔 🔔 🔔")
            await asyncio.sleep(1)
            await context.bot.send_message(user_id, "⏰ ПРОСЫПАЙСЯ! ⏰")
            await asyncio.sleep(1)
            await context.bot.send_message(user_id, "🌅 ДОБРОЕ УТРО! 🌅")

            # Отправляем головоломку
            await send_puzzle_to_user(user_id, context)

            # Деактивируем будильник до завтра
            db.deactivate_alarm(user_id)
            logger.info(f"Будильник сработал для {user_id} в {current_time_str}")

async def reset_daily_alarms(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневно в 00:01 активирует все будильники"""
    db.reset_all_alarms()
    logger.info("Все будильники сброшены на активное состояние")

def main():
    """Основная функция запуска бота"""
    # Создаем Application с job_queue
    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Фоновые задачи
    job_queue = application.job_queue

    if job_queue:
        job_queue.run_repeating(check_alarms, interval=60, first=10)  # Каждую минуту
        job_queue.run_daily(reset_daily_alarms, time=time(0, 1), days=tuple(range(7)))  # Каждый день в 00:01
        logger.info("✅ Фоновые задачи запущены!")
    else:
        logger.warning("⚠️ Job queue не доступен, будильники не будут работать")

    print("🤖 Бот 'Доброе утро' запущен!")
    print("📱 Иди в Telegram и напиши /start")

    application.run_polling()

if __name__ == "__main__":
    main()