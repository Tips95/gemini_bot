import aiohttp
from aiohttp import BasicAuth
import json
import uuid
from typing import Optional, Dict, Any
from loguru import logger
import os
from config import SUBSCRIPTION_PLANS

class YooKassaService:
    def __init__(self):
        def _clean(value: str) -> str:
            v = (value or "").strip()
            # удаляем обрамляющие кавычки, если есть
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1].strip()
            return v

        raw_shop_id = _clean(os.getenv("YOOKASSA_SHOP_ID") or "")
        # допускаем случайные недопустимые символы и удаляем всё, кроме цифр
        digits_only = "".join(ch for ch in raw_shop_id if ch.isdigit())
        self.shop_id = digits_only or raw_shop_id
        self.secret_key = _clean(os.getenv("YOOKASSA_SECRET_KEY") or "")
        self.base_url = "https://api.yookassa.ru/v3"
        # Для бота можно использовать ссылку на Telegram, либо наш /success маршрут
        self.return_url = os.getenv("RETURN_URL", "https://t.me/your_bot_username")
        if not self.return_url.startswith("http"):
            # Фоллбек на наш FastAPI маршрут успеха
            self.return_url = "https://your-app.example.com/success"
        
        if not self.shop_id or not self.secret_key:
            raise ValueError("YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY are required")
        if not self.shop_id.isdigit():
            raise ValueError("YOOKASSA_SHOP_ID должен содержать только цифры")
    
    def _get_headers(self) -> Dict[str, str]:
        """Базовые заголовки запроса (без Authorization — используем BasicAuth клиента)."""
        return {
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid.uuid4())
        }
    
    async def create_payment(self, user_id: int, plan_type: str, description: str = None) -> Optional[Dict[str, Any]]:
        """Создать платеж"""
        try:
            if plan_type not in SUBSCRIPTION_PLANS:
                logger.error(f"Invalid plan type: {plan_type}")
                return None
            
            plan = SUBSCRIPTION_PLANS[plan_type]
            amount = plan["price"]
            
            if not description:
                description = f"Подписка Gemini Image Editor - {plan['name']}"
            
            payment_data = {
                "amount": {
                    "value": f"{amount}.00",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": self.return_url
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "plan_type": plan_type,
                    "telegram_bot": "gemini_image_editor"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/payments",
                    headers=self._get_headers(),
                    auth=BasicAuth(self.shop_id, self.secret_key),
                    json=payment_data
                ) as response:
                    if response.status in (200, 201):
                        result = await response.json()
                        logger.info(f"Payment created for user {user_id}, plan {plan_type}")
                        return result
                    else:
                        error_text = await response.text()
                        if response.status == 401:
                            logger.error("YooKassa auth failed (401). Проверьте Shop ID, Secret Key и источник ключа (Merchant Profile).")
                        logger.error(f"Error creating payment: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error creating YooKassa payment: {e}")
            return None
    
    async def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус платежа"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/payments/{payment_id}",
                    headers=self._get_headers(),
                    auth=BasicAuth(self.shop_id, self.secret_key)
                ) as response:
                    if response.status in (200, 201):
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        if response.status == 401:
                            logger.error("YooKassa auth failed (401) on get status. Проверьте Shop ID/Secret Key.")
                        logger.error(f"Error getting payment status: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting YooKassa payment status: {e}")
            return None
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обработать webhook от YooKassa"""
        try:
            event_type = webhook_data.get("event")
            payment_data = webhook_data.get("object", {})
            
            if event_type == "payment.succeeded":
                payment_id = payment_data.get("id")
                metadata = payment_data.get("metadata", {})
                user_id = int(metadata.get("user_id"))
                plan_type = metadata.get("plan_type")
                amount = int(float(payment_data.get("amount", {}).get("value", 0)) * 100)  # в копейках
                
                logger.info(f"Payment succeeded: {payment_id} for user {user_id}, plan {plan_type}")
                
                return {
                    "user_id": user_id,
                    "plan_type": plan_type,
                    "payment_id": payment_id,
                    "amount": amount,
                    "currency": "RUB",
                    "status": "succeeded"
                }
            
            elif event_type == "payment.canceled":
                payment_id = payment_data.get("id")
                metadata = payment_data.get("metadata", {})
                user_id = int(metadata.get("user_id"))
                
                logger.info(f"Payment canceled: {payment_id} for user {user_id}")
                
                return {
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "status": "canceled"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling YooKassa webhook: {e}")
            return None
    
    def get_payment_url(self, payment_data: Dict[str, Any]) -> Optional[str]:
        """Получить URL для оплаты"""
        try:
            confirmation = payment_data.get("confirmation", {})
            if confirmation.get("type") == "redirect":
                return confirmation.get("confirmation_url")
            return None
        except Exception as e:
            logger.error(f"Error getting payment URL: {e}")
            return None
    
    async def create_refund(self, payment_id: str, amount: int, reason: str = "Refund") -> Optional[Dict[str, Any]]:
        """Создать возврат"""
        try:
            refund_data = {
                "amount": {
                    "value": f"{amount / 100:.2f}",
                    "currency": "RUB"
                },
                "payment_id": payment_id,
                "description": reason
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/refunds",
                    headers=self._get_headers(),
                    auth=BasicAuth(self.shop_id, self.secret_key),
                    json=refund_data
                ) as response:
                    if response.status in (200, 201):
                        result = await response.json()
                        logger.info(f"Refund created for payment {payment_id}")
                        return result
                    else:
                        error_text = await response.text()
                        if response.status == 401:
                            logger.error("YooKassa auth failed (401) on refund. Проверьте Shop ID/Secret Key.")
                        logger.error(f"Error creating refund: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error creating YooKassa refund: {e}")
            return None

    async def verify_credentials(self) -> bool:
        """Проверить авторизационные данные простым аутентифицированным запросом.
        Используем GET /payments?limit=1 как быструю проверку.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/payments?limit=1",
                    headers=self._get_headers(),
                    auth=BasicAuth(self.shop_id, self.secret_key)
                ) as response:
                    if response.status in (200, 201):
                        return True
                    error_text = await response.text()
                    logger.error(f"YooKassa credentials verification failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Error verifying YooKassa credentials: {e}")
            return False

# Ленивая инициализация сервиса, чтобы избежать падения при импорте модуля
yookassa_service: Optional[YooKassaService] = None

def init_yookassa_service() -> None:
    """Инициализировать глобальный экземпляр YooKassaService."""
    global yookassa_service
    if yookassa_service is None:
        yookassa_service = YooKassaService()

def get_yookassa_service() -> YooKassaService:
    """Вернуть инициализированный экземпляр сервиса YooKassa, инициализировав при необходимости."""
    global yookassa_service
    if yookassa_service is None:
        init_yookassa_service()
    return yookassa_service  # type: ignore[return-value]
