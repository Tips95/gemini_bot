import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")

# Replicate API (для генерации изображений)
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")

# YooMoney Payments
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# App Settings - Subscription Plans (in rubles)
SUBSCRIPTION_PLANS = {
    "1_month": {
        "price": 999,  # рублей
        "duration_days": 30,
        "name": "1 месяц"
    },
    "3_months": {
        "price": 1499,  # рублей
        "duration_days": 90,
        "name": "3 месяца"
    },
    "1_year": {
        "price": 4999,  # рублей
        "duration_days": 365,
        "name": "1 год"
    }
}

# Default plan
DEFAULT_PLAN = "1_month"

# Validation (deferred)
required_vars = [
    "BOT_TOKEN", "REPLICATE_API_KEY", "YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY", "DATABASE_URL"
]

def validate_config(required: list[str] | None = None) -> None:
    """Проверка обязательных переменных окружения. Бросает ValueError при отсутствии."""
    names_to_check = required or required_vars
    missing = [name for name in names_to_check if not os.getenv(name)]
    if missing:
        raise ValueError(f"Отсутствуют переменные окружения: {', '.join(missing)}")
