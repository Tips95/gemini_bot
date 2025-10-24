# 🚀 Деплой бота на VPS сервер

## 📋 **Пошаговая инструкция:**

### **1. Подключение к серверу:**
```bash
ssh root@90.156.225.217
```

### **2. Обновление системы:**
```bash
apt update && apt upgrade -y
apt install -y curl wget git nano htop software-properties-common
```

### **3. Установка Python 3.12:**
```bash
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.12 python3.12-pip python3.12-venv python3.12-dev
ln -s /usr/bin/python3.12 /usr/bin/python3
```

### **4. Создание пользователя для бота:**
```bash
useradd -m -s /bin/bash bot
mkdir -p /home/bot/app
chown -R bot:bot /home/bot
```

### **5. Клонирование проекта:**
```bash
su - bot
cd /home/bot
git clone https://github.com/Tips95/gemini_bot.git app
cd app
```

### **6. Настройка окружения:**
```bash
# Создание виртуального окружения
python3.12 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
nano .env
```

**Добавьте в .env файл:**
```bash
BOT_TOKEN=YOUR_BOT_TOKEN
REPLICATE_API_KEY=YOUR_REPLICATE_KEY
YOOKASSA_SHOP_ID=YOUR_SHOP_ID
YOOKASSA_SECRET_KEY=YOUR_SECRET_KEY
DATABASE_URL=sqlite:///bot_subscriptions.db
RETURN_URL=http://90.156.225.217:8000/success
```

### **7. Настройка firewall:**
```bash
# Возврат к root
exit

# Настройка UFW
ufw allow 22    # SSH
ufw allow 8000  # FastAPI
ufw --force enable
```

### **8. Создание systemd сервиса:**
```bash
nano /etc/systemd/system/telegram-bot.service
```

**Содержимое файла:**
```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/home/bot/app
Environment=PATH=/home/bot/app/venv/bin
ExecStart=/home/bot/app/venv/bin/python start_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### **9. Запуск бота:**
```bash
# Перезагрузка systemd
systemctl daemon-reload

# Включение автозапуска
systemctl enable telegram-bot

# Запуск бота
systemctl start telegram-bot

# Проверка статуса
systemctl status telegram-bot
```

### **10. Проверка работы:**
```bash
# Проверка логов
journalctl -u telegram-bot -f

# Проверка API
curl http://90.156.225.217:8000/
curl http://90.156.225.217:8000/health
```

## 🔗 **Webhook URL для YooKassa:**
```
http://90.156.225.217:8000/webhook/yookassa
```

## ✅ **Готово!**

После выполнения всех шагов ваш бот будет работать на сервере!
