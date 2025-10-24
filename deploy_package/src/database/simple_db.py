#!/usr/bin/env python3
"""
Простая база данных SQLite, совместимая с существующей системой подписок
"""

import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os
from loguru import logger
import asyncio

class SimpleDatabase:
    def __init__(self):
        self.db_path = "bot_subscriptions.db"
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица пользователей (совместимая с production_db)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'ru',
                    subscription_active BOOLEAN DEFAULT FALSE,
                    subscription_plan TEXT,
                    subscription_expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    plan_name TEXT,
                    price INTEGER,
                    duration_days INTEGER,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    payment_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            ''')
            
            # Таблица генераций изображений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    prompt TEXT,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            ''')
            
            # Таблица платежей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    payment_id TEXT UNIQUE,
                    amount INTEGER,
                    currency TEXT DEFAULT 'RUB',
                    status TEXT,
                    plan_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.success("Simple database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    # Асинхронные методы для совместимости с production_db
    async def add_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, language_code: str = 'ru'):
        """Добавить пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO users (telegram_id, username, first_name, last_name, language_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name, language_code))
            
            conn.commit()
            conn.close()
            logger.info(f"User {telegram_id} added/updated")
            
        except Exception as e:
            logger.error(f"Error adding user: {e}")
    
    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о пользователе"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'telegram_id': result[1],
                    'username': result[2],
                    'first_name': result[3],
                    'last_name': result[4],
                    'language_code': result[5],
                    'subscription_active': result[6],
                    'subscription_plan': result[7],
                    'subscription_expires_at': result[8],
                    'created_at': result[9],
                    'updated_at': result[10],
                    'last_activity': result[11]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def check_subscription(self, telegram_id: int) -> bool:
        """Проверить активную подписку"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT subscription_active, subscription_expires_at 
                FROM users 
                WHERE telegram_id = ? AND subscription_active = TRUE
            ''', (telegram_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                is_active, expires_at = result
                if is_active and expires_at:
                    expires_date = datetime.fromisoformat(expires_at)
                    if expires_date > datetime.now():
                        logger.info(f"Active subscription found for user {telegram_id}")
                        return True
            
            logger.info(f"No active subscription for user {telegram_id}")
            return False
                
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False
    
    async def create_subscription(self, telegram_id: int, plan_name: str, price: int, duration_days: int, payment_id: str = None) -> bool:
        """Создать подписку"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Деактивируем старые подписки
            cursor.execute('UPDATE users SET subscription_active = FALSE WHERE telegram_id = ?', (telegram_id,))
            
            # Создаем новую подписку
            expires_at = datetime.now() + timedelta(days=duration_days)
            cursor.execute('''
                INSERT INTO subscriptions (user_id, plan_name, price, duration_days, is_active, expires_at, payment_id)
                VALUES (?, ?, ?, ?, TRUE, ?, ?)
            ''', (telegram_id, plan_name, price, duration_days, expires_at, payment_id))
            
            # Обновляем пользователя
            cursor.execute('''
                UPDATE users 
                SET subscription_active = TRUE, subscription_plan = ?, subscription_expires_at = ?
                WHERE telegram_id = ?
            ''', (plan_name, expires_at, telegram_id))
            
            conn.commit()
            conn.close()
            logger.success(f"Subscription created for user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return False
    
    async def get_subscription_info(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о подписке"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT subscription_plan, subscription_expires_at, subscription_active
                FROM users 
                WHERE telegram_id = ?
            ''', (telegram_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                plan, expires_at, is_active = result
                return {
                    'plan': plan,
                    'expires_at': expires_at,
                    'is_active': is_active
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting subscription info: {e}")
            return None
    
    async def add_image_generation(self, telegram_id: int, prompt: str, image_url: str = None):
        """Добавить запись о генерации изображения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO image_generations (user_id, prompt, image_url)
                VALUES (?, ?, ?)
            ''', (telegram_id, prompt, image_url))
            
            conn.commit()
            conn.close()
            logger.info(f"Image generation recorded for user {telegram_id}")
            
        except Exception as e:
            logger.error(f"Error adding image generation: {e}")
    
    async def add_payment(self, telegram_id: int, payment_id: str, amount: int, status: str, plan_type: str):
        """Добавить запись о платеже"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO payments (user_id, payment_id, amount, status, plan_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, payment_id, amount, status, plan_type))
            
            conn.commit()
            conn.close()
            logger.info(f"Payment recorded for user {telegram_id}")
            
        except Exception as e:
            logger.error(f"Error adding payment: {e}")
    
    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Количество генераций
            cursor.execute('SELECT COUNT(*) FROM image_generations WHERE user_id = ?', (telegram_id,))
            generations_count = cursor.fetchone()[0]
            
            # Активная подписка
            subscription = await self.get_subscription_info(telegram_id)
            
            conn.close()
            
            return {
                'generations_count': generations_count,
                'has_active_subscription': subscription and subscription.get('is_active', False),
                'subscription': subscription
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'generations_count': 0, 'has_active_subscription': False, 'subscription': None}
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Создать пользователя (алиас для add_user)"""
        return await self.add_user(telegram_id, username, first_name, last_name)
    
    async def update_subscription(self, telegram_id: int, plan_name: str, duration_days: int, payment_id: str = None) -> bool:
        """Обновить подписку"""
        try:
            # Получаем цену плана из конфигурации
            from config import SUBSCRIPTION_PLANS
            if plan_name not in SUBSCRIPTION_PLANS:
                logger.error(f"Invalid plan: {plan_name}")
                return False
            
            plan = SUBSCRIPTION_PLANS[plan_name]
            price = plan['price']
            
            return await self.create_subscription(telegram_id, plan_name, price, duration_days, payment_id)
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
    
    async def log_image_generation(self, telegram_id: int, prompt: str, success: bool, image_url: str = None):
        """Логировать генерацию изображения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO image_generations (user_id, prompt, image_url)
                VALUES (?, ?, ?)
            ''', (telegram_id, prompt, image_url if success else None))
            
            conn.commit()
            conn.close()
            logger.info(f"Image generation logged for user {telegram_id}, success: {success}")
            
        except Exception as e:
            logger.error(f"Error logging image generation: {e}")

# Глобальный экземпляр базы данных
db = SimpleDatabase()
