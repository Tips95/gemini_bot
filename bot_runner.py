import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from loguru import logger
import os

from config import BOT_TOKEN, validate_config
from src.bot.handlers import router
from src.bot.middleware import LoggingMiddleware, RateLimitMiddleware
from src.database.simple_db import db
from src.services.yookassa_service import init_yookassa_service, yookassa_service

# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO"
)
logger.add(
    "logs/bot.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 day",
    retention="7 days"
)

async def main():
    """Основная функция запуска бота"""
    
    # Создаем директорию для логов
    os.makedirs("logs", exist_ok=True)
    
    # Проверяем обязательные переменные окружения
    try:
        validate_config()
    except Exception as e:
        logger.error(f"Конфигурация окружения недействительна: {e}")
        return
    
    # Инициализируем YooKassa после валидации окружения
    try:
        init_yookassa_service()
    except Exception as e:
        logger.error(f"Инициализация YooKassa не удалась: {e}")
        return
    
    # Инициализация базы данных (простая SQLite)
    try:
        # Простая база данных уже инициализирована в конструкторе
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    
    # Регистрируем middleware
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(RateLimitMiddleware(rate_limit=20, time_window=60))
    dp.callback_query.middleware(RateLimitMiddleware(rate_limit=30, time_window=60))
    
    # Регистрируем роутеры
    dp.include_router(router)
    
    # Уведомляем о запуске
    logger.info("Starting Gemini Image Editor Bot...")
    
    try:
        # Запускаем бота
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.session.close()
        # Простая база данных не требует закрытия пула
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
