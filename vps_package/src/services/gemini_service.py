import replicate
import asyncio
import time
from typing import Optional
from loguru import logger
from config import REPLICATE_API_KEY

class ReplicateImageService:
    def __init__(self):
        # Настройка Replicate с API ключом
        self.client = replicate.Client(api_token=REPLICATE_API_KEY)
        logger.info("Replicate service initialized")

    async def generate_image(self, prompt: str, user_id: int = None) -> Optional[str]:
        """Сгенерировать изображение через Replicate API"""
        try:
            logger.info(f"Generating image with Replicate: {prompt}")
            
            # Валидация промпта
            if len(prompt) < 5:
                logger.error("Prompt too short")
                return None
            
            # Создаем предсказание через официальную библиотеку
            output = self.client.run(
                "google/nano-banana",
                input={
                    "prompt": prompt,
                    "output_format": "png"
                }
            )
            
            if output:
                # Получаем URL изображения
                image_url = str(output)
                logger.success(f"Image generated successfully: {image_url}")
                return image_url
            else:
                logger.error("Failed to generate image")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None

    async def edit_image(self, prompt: str, image_url: str, user_id: int = None) -> Optional[str]:
        """Редактировать изображение через Replicate API"""
        try:
            logger.info(f"Editing image with Replicate: {prompt}")
            
            # Убеждаемся, что image_url это строка URL
            if isinstance(image_url, bytes):
                logger.error("Image URL is bytes, expected string URL")
                return None
            
            # Создаем предсказание для редактирования
            output = self.client.run(
                "google/nano-banana",
                input={
                    "prompt": prompt,
                    "image_input": [str(image_url)],
                    "output_format": "png"
                }
            )
            
            if output:
                # Получаем URL отредактированного изображения
                edited_url = str(output)
                logger.success(f"Image edited successfully: {edited_url}")
                return edited_url
            else:
                logger.error("Failed to edit image")
                return None
                
        except Exception as e:
            error_msg = str(e)
            if "sensitive" in error_msg.lower() or "flagged" in error_msg.lower():
                logger.warning(f"Image flagged as sensitive: {e}")
            else:
                logger.error(f"Error editing image: {e}")
            return None

# Глобальный экземпляр сервиса
replicate_service = ReplicateImageService()