# 🚀 Деплой на Timeweb Cloud

## 📦 Что загрузить на Timeweb:

### 1. Файлы проекта:
```
├── src/
│   ├── bot/
│   │   ├── handlers.py
│   │   └── middleware.py
│   ├── database/
│   │   └── simple_db.py
│   └── services/
│       ├── gemini_service.py
│       └── yookassa_service.py
├── app.py                 # FastAPI приложение (webhook'и)
├── bot_runner.py          # Запуск бота
├── config.py             # Конфигурация
├── requirements.txt      # Зависимости
└── env.timeweb.example   # Пример переменных
```

### 2. Настройка в Timeweb Cloud:

**Выберите:** FastAPI + Python 3.12

**Переменные окружения:**
```
BOT_TOKEN=your_telegram_bot_token
REPLICATE_API_KEY=your_replicate_api_key
YOOKASSA_SHOP_ID=your_yookassa_shop_id
YOOKASSA_SECRET_KEY=your_yookassa_secret_key
DATABASE_URL=sqlite:///bot_subscriptions.db
RETURN_URL=https://your-app.timeweb.cloud/success
```

### 3. После деплоя:

1. **База данных инициализируется автоматически** (SQLite)
2. **Бот запускается автоматически** через FastAPI
3. **Webhook URL для YooKassa:**
```
https://your-app.timeweb.cloud/webhook/yookassa
```

## 🔧 Команды для Timeweb:

**Проверка статуса:**
```bash
ps aux | grep python
```

**Проверка логов:**
```bash
tail -f logs/bot.log
```

**Перезапуск бота:**
```bash
pkill -f bot_runner.py
python bot_runner.py &
```

## ✅ Проверка работы:

1. **API:** `https://your-app.timeweb.cloud/`
2. **Health:** `https://your-app.timeweb.cloud/health`
3. **Webhook:** `https://your-app.timeweb.cloud/webhook/yookassa`

## 🎯 Готово!

После деплоя:
- ✅ Бот работает автоматически
- ✅ Webhook'и обрабатываются
- ✅ Подписки активируются автоматически
- ✅ Генерация и редактирование изображений работает
