import asyncio
import asyncpg
from loguru import logger
from config import DATABASE_URL

async def init_database():
    """Инициализация базы данных"""
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Создаем таблицы
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
        
        await conn.close()
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_database())
