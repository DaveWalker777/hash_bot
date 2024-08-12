import dhash
from PIL import Image
import sqlite3
from datetime import datetime, timedelta
import os


def create_db():
    conn = sqlite3.connect('image_hashes.db')
    c = conn.cursor()
    # Проверяем и создаем таблицу
    c.execute('''
        CREATE TABLE IF NOT EXISTS hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hash, chat_id)
        )
    ''')
    conn.commit()
    conn.close()


def is_hash_unique(new_hash_int, chat_id):
    conn = sqlite3.connect('image_hashes.db')
    c = conn.cursor()
    c.execute('SELECT hash, chat_id, date, message_id FROM hashes')
    rows = c.fetchall()
    conn.close()

    for row in rows:
        db_hash, db_chat_id, db_date, db_message_id = row
        db_hash_int = int(db_hash, 16)
        num_bits_diff = dhash.get_num_bits_different(new_hash_int, db_hash_int)
        if num_bits_diff <= 200:
            if db_chat_id == chat_id:
                return db_date, db_message_id, num_bits_diff
            else:
                return None, None, num_bits_diff  # Хэш совпадает, но чат отличается
    return None, None, None


def save_hash_to_db(image_hash, chat_id, message_id):
    conn = sqlite3.connect('image_hashes.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO hashes (hash, chat_id, message_id) VALUES (?, ?, ?)', (image_hash, chat_id, message_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Пропускаем дублирующие записи с одинаковыми хэшами в одном чате
    conn.close()


def add_hours_to_datetime(original_date, hours):
    original_datetime = datetime.fromisoformat(original_date)
    # Добавляем 3 часа
    new_datetime = original_datetime + timedelta(hours=hours)
    return new_datetime.strftime('%Y-%m-%d %H:%M:%S')


def format_chat_id(chat_id):
    # Удаляем префикс -100, если он есть
    chat_id_str = str(chat_id)
    if chat_id_str.startswith('-100'):
        return chat_id_str[4:]  # Удаляем первые 4 символа
    return chat_id_str


async def process_image(image_path, message_id, chat_id, bot):
    create_db()

    try:
        # Хэшируем изображение
        image = Image.open(image_path)
        row, col = dhash.dhash_row_col(image, size=32)
        image_hash = dhash.format_hex(row, col)
        image_hash_int = int(image_hash, 16)

        # Проверяем, уникален ли хэш изображения
        existing_date, existing_message_id, num_bits_diff = is_hash_unique(image_hash_int, chat_id)
        if existing_date:
            formatted_date = add_hours_to_datetime(existing_date, 3)
            formatted_chat_id = format_chat_id(chat_id)
            result_message = f"Ураха моментт, дата: {formatted_date}, разница в битах: {num_bits_diff}\nhttps://t.me/c/{formatted_chat_id}/{existing_message_id}"

            # Отправляем ответ на найденное сообщение в групповом чате
            await bot.send_message(chat_id, result_message, reply_to_message_id=existing_message_id)
        else:
            save_hash_to_db(image_hash, chat_id, message_id)
            return None
    finally:
        # Удаляем изображение независимо от результата
        if os.path.exists(image_path):
            os.remove(image_path)
