# 🚀 Инструкция по деплою на Timeweb Cloud

## 📦 Готовый пакет создан!

Папка `deploy_package` содержит все необходимые файлы для деплоя.

## 🔧 Пошаговая инструкция:

### 1. **Загрузка на Timeweb Cloud:**
- Зайдите в панель Timeweb Cloud
- Создайте новое приложение: **FastAPI + Python 3.12**
- Загрузите **все файлы** из папки `deploy_package`

### 2. **Настройка переменных окружения:**
В панели Timeweb добавьте:
```
BOT_TOKEN=your_telegram_bot_token
REPLICATE_API_KEY=your_replicate_api_key
YOOKASSA_SHOP_ID=your_yookassa_shop_id
YOOKASSA_SECRET_KEY=your_yookassa_secret_key
DATABASE_URL=sqlite:///bot_subscriptions.db
RETURN_URL=https://your-app.timeweb.cloud/success
```

### 3. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

### 4. **Запуск системы:**
```bash
python start_bot.py
```

## ✅ Проверка работы:

1. **API:** `https://your-app.timeweb.cloud/`
2. **Health:** `https://your-app.timeweb.cloud/health`
3. **Webhook:** `https://your-app.timeweb.cloud/webhook/yookassa`

## 🔗 Настройка YooKassa:

В настройках YooKassa укажите webhook URL:
```
https://your-app.timeweb.cloud/webhook/yookassa
```

## 🎯 Что работает после деплоя:

- ✅ **Telegram бот** - отвечает на команды
- ✅ **Генерация изображений** - через Replicate API
- ✅ **Редактирование изображений** - пользовательские фото
- ✅ **Система подписок** - с проверкой доступа
- ✅ **Автоматические платежи** - через YooKassa
- ✅ **Webhook'и** - автоматическая активация подписок

## 🚨 Важно:

1. **Замените `your-app`** на реальный домен Timeweb
2. **Проверьте все переменные** окружения
3. **Настройте webhook** в YooKassa
4. **Протестируйте** генерацию изображений

## 🎉 Готово!

Ваш бот будет работать на Timeweb Cloud с полной функциональностью!
