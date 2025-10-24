#!/usr/bin/env python3
"""
Скрипт для запуска бота на Timeweb Cloud
Запускает и бота, и FastAPI сервер одновременно
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

def start_fastapi():
    """Запуск FastAPI сервера для webhook'ов"""
    print("🚀 Запуск FastAPI сервера...")
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "app:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

def start_bot():
    """Запуск Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    return subprocess.Popen([
        sys.executable, "bot_runner.py"
    ])

async def main():
    """Главная функция"""
    print("🎯 Запуск системы на Timeweb Cloud...")
    
    # Создаем папку для логов
    os.makedirs("logs", exist_ok=True)
    
    # Запускаем FastAPI сервер
    fastapi_process = start_fastapi()
    
    # Ждем немного для запуска FastAPI
    await asyncio.sleep(3)
    
    # Запускаем бота
    bot_process = start_bot()
    
    print("✅ Система запущена!")
    print("📡 FastAPI: http://0.0.0.0:8000")
    print("🤖 Telegram Bot: активен")
    print("💳 Webhook: http://0.0.0.0:8000/webhook/yookassa")
    
    try:
        # Ждем завершения процессов
        await asyncio.gather(
            asyncio.create_task(asyncio.to_thread(fastapi_process.wait)),
            asyncio.create_task(asyncio.to_thread(bot_process.wait))
        )
    except KeyboardInterrupt:
        print("\n🛑 Остановка системы...")
        fastapi_process.terminate()
        bot_process.terminate()
        print("✅ Система остановлена")

if __name__ == "__main__":
    asyncio.run(main())
