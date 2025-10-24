#!/usr/bin/env python3
"""
Обновление пакета для VPS с исправлениями
"""

import os
import shutil
from pathlib import Path

def update_vps_package():
    """Обновляет пакет для VPS"""
    print("Updating VPS package with fixes...")
    
    # Файлы для деплоя
    deploy_files = [
        "src/",
        "app.py",
        "bot_runner.py", 
        "start_bot.py",
        "config.py",
        "requirements.txt",
        "README.md"
    ]
    
    # Создаем папку для деплоя
    deploy_dir = Path("vps_package")
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
    
    print(f"VPS package updated: {deploy_dir}")
    print("Ready for deployment!")

if __name__ == "__main__":
    update_vps_package()
