# Настройка Kie.ai API с Webhook

## Проблема
Kie.ai API работает **только через callback URL** - все endpoint'ы для проверки статуса возвращают 404.

## Решение
Использовать webhook сервер для получения результатов от Kie.ai Nano Banana API.

## Настройка

### 1. Получите webhook URL
Варианты:
- **webhook.site**: https://webhook.site - получите уникальный URL
- **ngrok**: `ngrok http 8000` - для локального тестирования  
- **Ваш сервер**: если у вас есть домен

### 2. Обновите callback URL
В файле `src/services/gemini_service.py` замените:
```python
"callBackUrl": "https://webhook.site/unique-url-here"
```
На ваш реальный webhook URL.

### 3. Запустите webhook сервер
```bash
python webhook_server.py
```

### 4. Запустите бота
```bash
python bot_runner.py
```

## Как это работает

1. **Пользователь отправляет промпт** в бот
2. **Бот создает задачу** в Kie.ai с callback URL
3. **Kie.ai обрабатывает** изображение через Nano Banana
4. **Kie.ai отправляет результат** на ваш webhook URL
5. **Webhook сервер получает** JSON с результатом
6. **Проверяет статус** (completed/failed)
7. **Скачивает изображение** и отправляет пользователю

## Структура webhook данных
```json
{
  "taskId": "task_id_here",
  "state": "completed",
  "output": {
    "images": [
      {
        "url": "https://example.com/image.png"
      }
    ]
  }
}
```

## Обработка ошибок
- `state: "failed"` → отправляется "❌ Ошибка генерации"
- Нет изображений → отправляется "❌ Изображения не найдены"
- Ошибка загрузки → отправляется "❌ Ошибка загрузки изображения"

## Примечания
- Webhook должен быть доступен из интернета
- HTTPS обязателен для production
- Проверьте логи webhook'а для отладки
- Реальные изображения от Nano Banana будут доставлены через webhook
