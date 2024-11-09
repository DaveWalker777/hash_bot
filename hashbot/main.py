import logging
from aiogram import Bot, Dispatcher, types
import aiohttp
import aiofiles
import asyncio
from pathlib import Path
from image_processing import process_image
from config import API_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
# test

@dp.message(lambda message: message.photo)
async def handle_photo(message: types.Message):
    chat_id = message.chat.id
    message_id = message.message_id
    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path

    # Получаем файл изображения из Telegram
    image_path = Path(file_id + '.jpg')
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}') as response:
            if response.status == 200:
                async with aiofiles.open(image_path, mode='wb') as f:
                    await f.write(await response.read())
            else:
                await message.reply("Ошибка при загрузке изображения.")
                return

    # Обрабатываем изображение
    result_message = await process_image(image_path, message_id, chat_id, bot)

    # Удаление локального файла
    if image_path.exists():
        image_path.unlink()


async def on_startup(dispatcher: Dispatcher):
    logging.info("Bot is starting...")


async def on_shutdown(dispatcher: Dispatcher):
    logging.info("Bot is shutting down...")


async def main():
    # Запуск бота
    await dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == '__main__':
    asyncio.run(main())
