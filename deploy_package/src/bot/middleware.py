from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from loguru import logger
import time

class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования запросов"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        # Логируем входящий запрос
        if isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username or "Unknown"
            text = event.text or "No text"
            logger.info(f"Message from {username} ({user_id}): {text[:50]}...")
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            username = event.from_user.username or "Unknown"
            data_text = event.data or "No data"
            logger.info(f"Callback from {username} ({user_id}): {data_text}")
        
        try:
            # Выполняем обработчик
            result = await handler(event, data)
            
            # Логируем время выполнения
            execution_time = time.time() - start_time
            logger.info(f"Handler executed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Логируем ошибки
            execution_time = time.time() - start_time
            logger.error(f"Handler error after {execution_time:.2f}s: {e}")
            raise

class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self, rate_limit: int = 10, time_window: int = 60):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.user_requests = {}  # {user_id: [timestamps]}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        
        # Очищаем старые запросы
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                timestamp for timestamp in self.user_requests[user_id]
                if current_time - timestamp < self.time_window
            ]
        else:
            self.user_requests[user_id] = []
        
        # Проверяем лимит
        if len(self.user_requests[user_id]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            
            if isinstance(event, Message):
                await event.answer(
                    "⏰ Слишком много запросов. Подожди немного и попробуй снова.",
                    show_alert=True
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⏰ Слишком много запросов. Подожди немного и попробуй снова.",
                    show_alert=True
                )
            
            return
        
        # Добавляем текущий запрос
        self.user_requests[user_id].append(current_time)
        
        # Выполняем обработчик
        return await handler(event, data)

class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки (опционально)"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Этот middleware можно использовать для автоматической проверки подписки
        # на определенных командах, но пока оставляем проверку в обработчиках
        
        return await handler(event, data)
