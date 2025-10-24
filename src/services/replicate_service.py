#!/usr/bin/env python3
"""
Сервис для генерации изображений через Replicate API
"""

import os
import requests
import time
import asyncio
from typing import Optional
from loguru import logger
from config import REPLICATE_API_KEY

class ReplicateImageService:
    def __init__(self):
        self.api_key = REPLICATE_API_KEY
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Популярные модели для генерации изображений
        self.models = {
            'stable-diffusion': 'stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478',
            'sdxl': 'stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b',
            'flux': 'black-forest-labs/flux:36d42d23d8ec4e2745e8e79ebde4bae3f9c46e6a'
        }
    
    async def generate_image(self, prompt: str, model: str = 'stable-diffusion') -> Optional[str]:
        """Сгенерировать изображение через Replicate API"""
        try:
            logger.info(f"Generating image with Replicate: {prompt}")
            
            # Валидация промпта
            if len(prompt) < 5:
                logger.error("Prompt too short")
                return None
            
            # Выбираем модель
            model_version = self.models.get(model, self.models['stable-diffusion'])
            
            # Создаем предсказание
            prediction = await self._create_prediction(prompt, model_version)
            if not prediction:
                logger.error("Failed to create prediction")
                return None
            
            prediction_id = prediction['id']
            logger.info(f"Prediction created: {prediction_id}")
            
            # Ждем завершения и получаем результат
            result = await self._wait_for_completion(prediction_id)
            if result:
                logger.success(f"Image generated successfully: {result}")
                return result
            else:
                logger.error("Failed to generate image")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None
    
    async def _create_prediction(self, prompt: str, model_version: str) -> Optional[dict]:
        """Создать предсказание в Replicate"""
        try:
            # Параметры для разных моделей
            if 'stable-diffusion' in model_version:
                input_data = {
                    "prompt": prompt,
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 20,
                    "guidance_scale": 7.5
                }
            elif 'sdxl' in model_version:
                input_data = {
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "num_inference_steps": 25,
                    "guidance_scale": 7.5
                }
            elif 'flux' in model_version:
                input_data = {
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "num_inference_steps": 20
                }
            else:
                input_data = {"prompt": prompt}
            
            payload = {
                "version": model_version,
                "input": input_data
            }
            
            response = requests.post(
                f"{self.base_url}/predictions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                logger.info(f"Prediction created successfully: {result['id']}")
                return result
            else:
                logger.error(f"Failed to create prediction: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating prediction: {e}")
            return None
    
    async def _wait_for_completion(self, prediction_id: str, max_wait_time: int = 300) -> Optional[str]:
        """Ждать завершения предсказания и получить результат"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                logger.info(f"Checking prediction {prediction_id} status...")
                
                response = requests.get(
                    f"{self.base_url}/predictions/{prediction_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    prediction = response.json()
                    status = prediction.get('status')
                    
                    logger.info(f"Prediction status: {status}")
                    
                    if status == 'succeeded':
                        # Получаем URL изображения
                        output = prediction.get('output')
                        if output:
                            if isinstance(output, list) and len(output) > 0:
                                image_url = output[0]
                            elif isinstance(output, str):
                                image_url = output
                            else:
                                logger.error(f"Unexpected output format: {output}")
                                return None
                            
                            logger.success(f"Image ready: {image_url}")
                            return image_url
                        else:
                            logger.error("No output in successful prediction")
                            return None
                    
                    elif status == 'failed':
                        error = prediction.get('error', 'Unknown error')
                        logger.error(f"Prediction failed: {error}")
                        return None
                    
                    elif status in ['starting', 'processing']:
                        # Предсказание еще выполняется
                        await asyncio.sleep(5)  # Ждем 5 секунд
                        continue
                    
                    else:
                        logger.warning(f"Unknown status: {status}")
                        await asyncio.sleep(5)
                        continue
                else:
                    logger.error(f"Failed to check prediction status: {response.status_code}")
                    await asyncio.sleep(5)
                    continue
            
            # Превышено время ожидания
            logger.error(f"Prediction timeout after {max_wait_time} seconds")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
            return None
    
    async def get_available_models(self) -> dict:
        """Получить список доступных моделей"""
        return self.models

# Глобальный экземпляр сервиса
replicate_service = ReplicateImageService()
