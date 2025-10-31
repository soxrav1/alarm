import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.init_database()

    def init_database(self):
        """Инициализация базы данных SQLite"""
        conn = sqlite3.connect('alarm_bot.db')
        cursor = conn.cursor()

        # УДАЛЯЕМ старые таблицы если есть
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS alarms")
        cursor.execute("DROP TABLE IF EXISTS user_states")
        cursor.execute("DROP TABLE IF EXISTS statistics")

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                created_at TEXT
            )
        ''')

        # Таблица будильников
        cursor.execute('''
            CREATE TABLE alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                time_start TEXT,
                time_end TEXT,
                random_wake_time TEXT,
                last_activation_date TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT
            )
        ''')

        # Таблица состояний пользователей
        cursor.execute('''
            CREATE TABLE user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT DEFAULT 'SLEEP',
                current_puzzle_question TEXT,
                current_puzzle_answer TEXT,
                puzzle_sent_at TEXT
            )
        ''')

        # Таблица статистики
        cursor.execute('''
            CREATE TABLE statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                status TEXT,
                solve_time_1 INTEGER,
                solve_time_2 INTEGER
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("✅ База данных пересоздана с правильной структурой!")

    def get_connection(self):
        """Возвращает соединение с базой данных"""
        return sqlite3.connect('alarm_bot.db')

    def save_user(self, user_id: int, first_name: str, username: str):
        """Сохранить пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, first_name, username, created_at) VALUES (?, ?, ?, ?)",
            (user_id, first_name, username, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_user_state(self, user_id: int):
        """Получить состояние пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT state, current_puzzle_question, current_puzzle_answer FROM user_states WHERE user_id = ?",
            (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'state': result[0],
                'current_puzzle_question': result[1],
                'current_puzzle_answer': result[2]
            }
        return None

    def set_user_state(self, user_id: int, state: str, puzzle_question: str = None, puzzle_answer: str = None):
        """Установить состояние пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if puzzle_question and puzzle_answer:
            cursor.execute('''
                INSERT OR REPLACE INTO user_states 
                (user_id, state, current_puzzle_question, current_puzzle_answer, puzzle_sent_at) 
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, state, puzzle_question, puzzle_answer, datetime.now().isoformat()))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO user_states 
                (user_id, state, puzzle_sent_at) 
                VALUES (?, ?, ?)
            ''', (user_id, state, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def set_alarm(self, user_id: int, time_start: str, time_end: str):
        """Установить будильник"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Удаляем старый будильник
        cursor.execute("DELETE FROM alarms WHERE user_id = ?", (user_id,))

        # Создаем новый с дополнительными полями
        cursor.execute(
            "INSERT INTO alarms (user_id, time_start, time_end, random_wake_time, last_activation_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, time_start, time_end, None, None, datetime.now().isoformat())
        )

        conn.commit()
        conn.close()
        logger.info(f"Будильник установлен для пользователя {user_id}: {time_start} - {time_end}")

    def get_active_alarms(self):
        """Получить все активные будильники"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, time_start, time_end, random_wake_time, last_activation_date FROM alarms WHERE is_active = TRUE")
        alarms = cursor.fetchall()
        conn.close()
        return alarms

    def update_alarm_wake_time(self, user_id: int, wake_time: str, activation_date: str):
        """Обновить время пробуждения будильника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alarms SET random_wake_time = ?, last_activation_date = ? WHERE user_id = ?",
            (wake_time, activation_date, user_id)
        )
        conn.commit()
        conn.close()

    def deactivate_alarm(self, user_id: int):
        """Деактивировать будильник"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alarms SET is_active = FALSE WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def reset_all_alarms(self):
        """Активировать все будильники (ежедневный сброс)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alarms SET is_active = TRUE, random_wake_time = NULL")
        conn.commit()
        conn.close()
        logger.info("Все будильники сброшены на активное состояние")

    def add_statistics(self, user_id: int, status: str):
        """Добавить запись в статистику"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO statistics (user_id, date, status) VALUES (?, ?, ?)",
            (user_id, datetime.now().isoformat(), status)
        )
        conn.commit()
        conn.close()

    def get_statistics(self, user_id: int):
        """Получить статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM statistics WHERE user_id = ? ORDER BY date DESC LIMIT 7",
            (user_id,)
        )
        results = cursor.fetchall()
        conn.close()

        success = len([r for r in results if r[0] == 'success'])
        failed_first = len([r for r in results if r[0] == 'failed_first'])
        failed_second = len([r for r in results if r[0] == 'failed_second'])

        return success, failed_first, failed_second