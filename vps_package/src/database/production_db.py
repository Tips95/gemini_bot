import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os
from loguru import logger
import asyncio

class ProductionDatabase:
    def __init__(self):
        self.pool = None
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    async def init_pool(self):
        """Инициализация пула соединений"""
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            await self.create_tables()
            logger.info("Database pool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database pool: {e}")
            raise
    
    async def create_tables(self):
        """Создание таблиц"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем таблицу пользователей
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        language_code VARCHAR(10) DEFAULT 'ru',
                        subscription_active BOOLEAN DEFAULT FALSE,
                        subscription_plan VARCHAR(50),
                        subscription_expires_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                ''')
                
                # Создаем таблицу для логирования генерации изображений
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS image_generations (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        prompt TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        generation_type VARCHAR(50) DEFAULT 'text_to_image',
                        processing_time_ms INTEGER,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )
                ''')
                
                # Создаем таблицу для логирования платежей
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        payment_id VARCHAR(255) UNIQUE NOT NULL,
                        plan_type VARCHAR(50) NOT NULL,
                        amount INTEGER NOT NULL,
                        currency VARCHAR(3) DEFAULT 'RUB',
                        status VARCHAR(50) NOT NULL,
                        payment_method VARCHAR(50),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        processed_at TIMESTAMP WITH TIME ZONE,
                        FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                    )
                ''')
                
                # Создаем таблицу для статистики
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL UNIQUE,
                        total_users INTEGER DEFAULT 0,
                        active_users INTEGER DEFAULT 0,
                        new_users INTEGER DEFAULT 0,
                        total_generations INTEGER DEFAULT 0,
                        successful_generations INTEGER DEFAULT 0,
                        total_revenue INTEGER DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                ''')
                
                # Создаем индексы
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_active, subscription_expires_at)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_activity ON users(last_activity)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_image_generations_user_id ON image_generations(user_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_image_generations_created_at ON image_generations(created_at)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)')
                
                # Создаем функцию для автоматического обновления updated_at
                await conn.execute('''
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = NOW();
                        NEW.last_activity = NOW();
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                ''')
                
                # Создаем триггеры
                await conn.execute('''
                    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
                    CREATE TRIGGER update_users_updated_at 
                        BEFORE UPDATE ON users 
                        FOR EACH ROW 
                        EXECUTE FUNCTION update_updated_at_column();
                ''')
                
                logger.info("Database tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    async def close_pool(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM users WHERE telegram_id = $1', user_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def create_user(self, user_id: int, username: str, first_name: str, 
                         last_name: str = None, language_code: str = 'ru') -> bool:
        """Создать нового пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name, language_code, 
                                     subscription_active, subscription_expires_at, created_at, updated_at, last_activity)
                    VALUES ($1, $2, $3, $4, $5, FALSE, NULL, NOW(), NOW(), NOW())
                    ON CONFLICT (telegram_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        language_code = EXCLUDED.language_code,
                        last_activity = NOW()
                ''', user_id, username, first_name, last_name, language_code)
                return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def update_subscription(self, user_id: int, plan_type: str, active: bool, 
                                 duration_days: int = None) -> bool:
        """Обновить подписку пользователя"""
        try:
            from datetime import timezone
            expires_at = None
            if active and duration_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE users 
                    SET subscription_active = $1, subscription_plan = $2, 
                        subscription_expires_at = $3, updated_at = NOW(), last_activity = NOW()
                    WHERE telegram_id = $4
                ''', active, plan_type, expires_at, user_id)
                return True
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
    
    async def check_subscription(self, user_id: int) -> bool:
        """Проверить активность подписки"""
        try:
            user = await self.get_user(user_id)
            if not user:
                logger.info(f"User {user_id} not found")
                return False
            
            subscription_active = user.get('subscription_active')
            logger.info(f"User {user_id} subscription_active: {subscription_active}")
            
            if not subscription_active:
                return False
            
            expires_at = user.get('subscription_expires_at')
            logger.info(f"User {user_id} expires_at: {expires_at}")
            
            if not expires_at:
                return False
            
            # Проверяем, не истекла ли подписка
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            logger.info(f"Current time UTC: {now_utc}")
            
            # Если expires_at строка, парсим её
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
            logger.info(f"Parsed expires_at: {expires_at}")
            
            if expires_at < now_utc:
                logger.info(f"Subscription expired for user {user_id}")
                # Автоматически деактивируем истекшую подписку
                await self.update_subscription(user_id, user.get('subscription_plan', ''), False)
                return False
            
            logger.info(f"Subscription valid for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False
    
    async def log_image_generation(self, user_id: int, prompt: str, success: bool, 
                                  generation_type: str = 'text_to_image', 
                                  processing_time_ms: int = None) -> bool:
        """Логировать генерацию изображения"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO image_generations (user_id, prompt, success, generation_type, processing_time_ms, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                ''', user_id, prompt, success, generation_type, processing_time_ms)
                return True
        except Exception as e:
            logger.error(f"Error logging image generation: {e}")
            return False
    
    async def log_payment(self, user_id: int, payment_id: str, plan_type: str, 
                         amount: int, currency: str, status: str, 
                         payment_method: str = None) -> bool:
        """Логировать платеж"""
        try:
            processed_at = datetime.utcnow() if status == 'succeeded' else None
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO payments (user_id, payment_id, plan_type, amount, currency, 
                                        status, payment_method, created_at, processed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8)
                ''', user_id, payment_id, plan_type, amount, currency, status, payment_method, processed_at)
                return True
        except Exception as e:
            logger.error(f"Error logging payment: {e}")
            return False
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Статистика генераций
                gen_stats = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_generations,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_generations,
                        AVG(processing_time_ms) as avg_processing_time
                    FROM image_generations 
                    WHERE user_id = $1
                ''', user_id)
                
                # Статистика платежей
                pay_stats = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_payments,
                        SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) as total_paid_amount
                    FROM payments 
                    WHERE user_id = $1
                ''', user_id)
                
                return {
                    'total_generations': gen_stats['total_generations'] or 0,
                    'successful_generations': gen_stats['successful_generations'] or 0,
                    'avg_processing_time': gen_stats['avg_processing_time'] or 0,
                    'total_payments': pay_stats['total_payments'] or 0,
                    'total_paid_amount': pay_stats['total_paid_amount'] or 0
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Получить административную статистику"""
        try:
            async with self.pool.acquire() as conn:
                # Общая статистика
                stats = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN subscription_active = true THEN 1 END) as active_subscribers,
                        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as new_users_24h,
                        COUNT(CASE WHEN last_activity >= NOW() - INTERVAL '24 hours' THEN 1 END) as active_users_24h
                    FROM users
                ''')
                
                # Статистика генераций за последние 24 часа
                gen_stats = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_generations_24h,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_generations_24h
                    FROM image_generations 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                ''')
                
                # Статистика доходов
                revenue_stats = await conn.fetchrow('''
                    SELECT 
                        SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) as total_revenue,
                        SUM(CASE WHEN status = 'succeeded' AND created_at >= NOW() - INTERVAL '24 hours' THEN amount ELSE 0 END) as revenue_24h
                    FROM payments
                ''')
                
                return {
                    'total_users': stats['total_users'] or 0,
                    'active_subscribers': stats['active_subscribers'] or 0,
                    'new_users_24h': stats['new_users_24h'] or 0,
                    'active_users_24h': stats['active_users_24h'] or 0,
                    'total_generations_24h': gen_stats['total_generations_24h'] or 0,
                    'successful_generations_24h': gen_stats['successful_generations_24h'] or 0,
                    'total_revenue': revenue_stats['total_revenue'] or 0,
                    'revenue_24h': revenue_stats['revenue_24h'] or 0
                }
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            return {}
    
    async def update_daily_stats(self):
        """Обновить ежедневную статистику"""
        try:
            today = datetime.utcnow().date()
            
            async with self.pool.acquire() as conn:
                # Получаем статистику за сегодня
                stats = await conn.fetchrow('''
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN subscription_active = true THEN 1 END) as active_users,
                        COUNT(CASE WHEN created_at::date = $1 THEN 1 END) as new_users,
                        (SELECT COUNT(*) FROM image_generations WHERE created_at::date = $1) as total_generations,
                        (SELECT COUNT(*) FROM image_generations WHERE created_at::date = $1 AND success = true) as successful_generations,
                        (SELECT SUM(amount) FROM payments WHERE created_at::date = $1 AND status = 'succeeded') as total_revenue
                    FROM users
                ''', today)
                
                # Вставляем или обновляем статистику
                await conn.execute('''
                    INSERT INTO daily_stats (date, total_users, active_users, new_users, 
                                           total_generations, successful_generations, total_revenue)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (date) DO UPDATE SET
                        total_users = EXCLUDED.total_users,
                        active_users = EXCLUDED.active_users,
                        new_users = EXCLUDED.new_users,
                        total_generations = EXCLUDED.total_generations,
                        successful_generations = EXCLUDED.successful_generations,
                        total_revenue = EXCLUDED.total_revenue
                ''', today, stats['total_users'], stats['active_users'], stats['new_users'],
                    stats['total_generations'], stats['successful_generations'], stats['total_revenue'])
                
                logger.info(f"Daily stats updated for {today}")
                
        except Exception as e:
            logger.error(f"Error updating daily stats: {e}")

# Глобальный экземпляр базы данных
db = ProductionDatabase()
