import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импорты движка базы данных и middleware
from tg_bot.database.engine import init_db, create_session_maker
from tg_bot.middlewares.db import DbSessionMiddleware
from tg_bot.database.seed import seed_database 
# Импорты роутеров (хендлеров)
from tg_bot.handlers.start import start_router
from tg_bot.handlers.admin import admin_router

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

async def main():
    # 1. Загрузка переменных окружения
    load_dotenv()
    
    bot_token = os.getenv("BOT_TOKEN")
    db_url = os.getenv("DB_URL", "sqlite+aiosqlite:///./bot_database.db")
    
    if not bot_token:
        logger.error("BOT_TOKEN не найден в .env файле!")
        return

    # 2. Инициализация бота и диспетчера
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 3. База данных
    logger.info("Подключение к базе данных...")
    await init_db(db_url)
    session_maker = create_session_maker(db_url)

    async with session_maker() as session:
        await seed_database(session)

    # 4. Регистрация Middleware (передаем сессию БД в хендлеры)
    dp.update.middleware(DbSessionMiddleware(session_maker=session_maker))

    # 5. Регистрация роутеров
    # ВАЖНО: Порядок имеет значение. Сначала админский, потом основной.
    # Мы включаем каждый роутер строго ОДИН РАЗ.
    dp.include_router(admin_router)
    dp.include_router(start_router)

    # 6. Запуск бота
    logger.info("Запуск бота...")
    
    # Удаляем вебхуки и пропускаем старые сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот выключен пользователем")