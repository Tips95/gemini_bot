#!/usr/bin/env python3
"""
Скрипт для подготовки проекта к деплою на Timeweb Cloud
"""

import os
import shutil
from pathlib import Path

def create_deploy_package():
    """Создает пакет для деплоя"""
    print("Creating deployment package...")
    
    # Файлы для деплоя
    deploy_files = [
        "src/",
        "app.py",
        "bot_runner.py", 
        "start_bot.py",
        "config.py",
        "requirements.txt",
        "env.timeweb.example",
        "DEPLOY_TIMEWEB.md"
    ]
    
    # Создаем папку для деплоя
    deploy_dir = Path("deploy_package")
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir()
    
    # Копируем файлы
    for file_path in deploy_files:
        src = Path(file_path)
        dst = deploy_dir / file_path
        
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    
    # Создаем папку для логов
    (deploy_dir / "logs").mkdir()
    
    print(f"Package created in folder: {deploy_dir}")
    print("\nNext steps:")
    print("1. Upload contents of deploy_package folder to Timeweb Cloud")
    print("2. Set environment variables in Timeweb panel")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Run: python start_bot.py")
    print("\nWebhook URL for YooKassa:")
    print("https://your-app.timeweb.cloud/webhook/yookassa")

if __name__ == "__main__":
    create_deploy_package()
