import os
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройки времени
FIRST_PUZZLE_TIMEOUT = 10 * 60  # 10 минут в секундах
SECOND_PUZZLE_TIMEOUT = 7 * 60  # 7 минут в секундах
DELAY_BETWEEN_PUZZLES = 10 * 60  # 10 минут между головоломками