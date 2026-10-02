# 🎮 Gaming Club - Quick Start Guide

## ⚡ Быстрый запуск (Windows)

Просто запустите файл `start_all.bat` - он автоматически запустит все сервисы:

- Django Backend (порт 8000)
- Telegram Bot

```bash
# Двойной клик на файл или в терминале:
start_all.bat
```

## 🔧 Ручной запуск

### Вариант 1: Два терминала

**Терминал 1 - Backend:**

```bash
python manage.py runserver
```

**Терминал 2 - Telegram Bot:**

```bash
cd tg_bot
node index.js
```

### Вариант 2: PowerShell (параллельно)

```powershell
# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python manage.py runserver"

# Bot
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd tg_bot; node index.js"
```

## 📍 Доступные URL

После запуска:

- **Backend API:** http://127.0.0.1:8000/api/
- **Главная страница:** http://127.0.0.1:8000/
- **Дашборд:** http://127.0.0.1:8000/dashboard/
- **Супер-дашборд:** http://127.0.0.1:8000/super/
- **Admin:** http://127.0.0.1:8000/admin/

## ✅ Проверка работы

### 1. Проверка Backend

Откройте в браузере: http://127.0.0.1:8000/api/place_status/

Должен вернуться JSON с местами.

### 2. Проверка Telegram Bot

Напишите боту `/start` в Telegram.

## 🛑 Остановка сервисов

### Если запускали через start_all.bat:

Нажмите любую клавишу в окне скрипта.

### Если запускали вручную:

Нажмите `Ctrl+C` в каждом терминале.

## 🔍 Troubleshooting

### Backend не запускается

```bash
# Проверьте установку зависимостей
pip install -r requirements.txt

# Примените миграции
python manage.py migrate
```

### Bot не запускается

```bash
cd tg_bot

# Проверьте зависимости
npm install

# Проверьте .env файл
# Должен содержать: BOT_TOKEN=your_token
```

### Порт уже занят

```bash
# Для Windows - найти и убить процесс на порту 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

## 📦 Первый запуск

При первом запуске выполните:

```bash
# 1. Установите Python зависимости
pip install -r requirements.txt

# 2. Примените миграции
python manage.py migrate

# 3. (Опционально) Создайте тестовые данные
python setup_tariffs.py
python setup_places.py

# 4. Установите Node.js зависимости для бота
cd tg_bot
npm install
cd ..

# 5. Настройте .env для бота
# Создайте файл tg_bot/.env с содержимым:
# BOT_TOKEN=your_telegram_bot_token

# 6. Запустите все сервисы
start_all.bat
```

## 🎯 Следующие шаги

1. **Создайте суперпользователя для админки:**

   ```bash
   python manage.py createsuperuser
   ```

2. **Настройте тарифы и места через админку:**
   http://127.0.0.1:8000/admin/

3. **Протестируйте бота:**
   Отправьте `/start` вашему боту в Telegram

## 🚀 Готово к разработке!

Все сервисы запущены и готовы к работе. Удачи! 🎉
