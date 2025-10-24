# Настройка Kie.ai API для генерации изображений

## Шаг 1: Получение API ключа Nano Banana

1. Зарегистрируйтесь на [Kie.ai](https://kie.ai/)
2. Получите защищённый ключ Nano Banana API
3. Убедитесь, что у ключа есть доступ к генерации изображений

## Шаг 2: Настройка переменных окружения

Создайте файл `.env` в корне проекта со следующими переменными:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# Database (PostgreSQL)
DATABASE_URL=postgresql://gen_user:Qanuqima25@192.168.0.4:5432/default_db

# Kie.ai API (для всех операций с изображениями)
KIE_API_KEY=your_nano_banana_api_key_here

# Опциональный callback URL для доставки результатов генерации
KIE_CALLBACK_URL=https://your-domain.com/callback

# YooMoney Payments
YOOKASSA_SHOP_ID=1187406
YOOKASSA_SECRET_KEY=live_g4_m6ILJ7CJcmHSzRq-qxNUXnu1qiPSaaqqtKJOfCFA

# Return URL для платежей
RETURN_URL=https://t.me/your_bot_username
```

## Шаг 3: Настройка callback URL (опционально)

### Вариант 1: Использование ngrok (для тестирования)
1. Установите ngrok: https://ngrok.com/
2. Запустите: `ngrok http 8080`
3. Скопируйте HTTPS URL (например: `https://abc123.ngrok.io`)
4. Установите в `.env`: `KIE_CALLBACK_URL=https://abc123.ngrok.io/callback`

### Вариант 2: Использование webhook.site (для тестирования)
1. Откройте https://webhook.site/
2. Скопируйте уникальный URL
3. Установите в `.env`: `KIE_CALLBACK_URL=https://webhook.site/your-unique-url`

### Вариант 3: Собственный сервер
1. Разверните сервер с endpoint `/callback`
2. Установите в `.env`: `KIE_CALLBACK_URL=https://your-domain.com/callback`

## Текущий статус

✅ **Бот работает с заглушками** - генерация и редактирование изображений работают  
✅ **Все функции бота активны** - подписки, платежи, база данных  
⚠️ **Нужен реальный API ключ** - для полной работы с Kie.ai API  

## Тестирование

1. Запустите бота: `python bot_runner.py`
2. Найдите бота в Telegram
3. Отправьте команду `/start`
4. Попробуйте генерацию изображений

## Структура API запросов

### Генерация изображения
```json
{
  "model": "google/nano-banana",
  "callBackUrl": "https://your-domain.com/callback",
  "input": {
    "prompt": "A beautiful sunset over the ocean"
  }
}
```

### Редактирование изображения
```json
{
  "model": "google/nano-banana", 
  "callBackUrl": "https://your-domain.com/callback",
  "input": {
    "prompt": "Edit this image: make it more colorful",
    "image": "base64_encoded_image_data"
  }
}
```

## Поддержка

Если возникли проблемы:
1. Проверьте логи в `logs/bot.log`
2. Убедитесь, что все переменные окружения установлены
3. Проверьте доступность API ключа на Kie.ai
