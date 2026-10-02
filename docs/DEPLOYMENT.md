# 🚀 Руководство по развёртыванию CRM PlayStation Club

## 📋 Требования

- Python 3.10+
- Node.js 18+
- Docker (опционально)
- PostgreSQL (опционально, по умолчанию SQLite)

---

## 🐍 Backend (Django)

### Локальная разработка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Миграции
python manage.py makemigrations
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Запуск
python manage.py runserver
```

### Docker

```bash
# Сборка и запуск
docker-compose up -d

# Миграции
docker-compose exec backend python manage.py migrate

# Создание суперпользователя
docker-compose exec backend python manage.py createsuperuser
```

---

## 🤖 Telegram Bot

### Локальная разработка

```bash
cd tg_bot

# Установка зависимостей
npm install

# Настройка
cp .env.example .env
# Отредактируйте .env и добавьте BOT_TOKEN

# Запуск
node index.js
```

### Docker

```bash
docker-compose up -d bot
```

---

## 🌐 Production

### Railway

1. Создайте проект на [Railway](https://railway.app)
2. Подключите GitHub репозиторий
3. Настройте переменные окружения:
   - `DJANGO_DEBUG=False`
   - `DJANGO_SECRET_KEY=<your-secret-key>`
   - `DJANGO_ALLOWED_HOSTS=<your-domain>`
   - `BOT_TOKEN=<your-bot-token>`

### Render

1. Создайте Web Service на [Render](https://render.com)
2. Подключите GitHub репозиторий
3. Настройте переменные окружения

### VPS

```bash
# Клонирование
git clone https://github.com/gggmuk/crm_for_psclub.git
cd crm_for_psclub

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000

# Bot
cd tg_bot
npm install
pm2 start index.js --name "crm-psclub-bot"
```

---

## 🔐 Переменные окружения

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `DJANGO_DEBUG` | Режим отладки | Да |
| `DJANGO_SECRET_KEY` | Секретный ключ Django | Да |
| `DJANGO_ALLOWED_HOSTS` | Разрешённые хосты | Да |
| `BOT_TOKEN` | Токен Telegram бота | Да |
| `CRM_API_KEY` | API ключ для менеджерских эндпоинтов | Да |
| `DATABASE_URL` | URL базы данных | Нет |

---

## 📊 Мониторинг

- **Backend:** Django Admin `/admin/`
- **Bot:** Логи в консоли
- **Ошибки:** Sentry (если настроен)

---

## 🔄 CI/CD

Проект настроен для автоматического тестирования через GitHub Actions:

- Python тесты (pytest)
- Node.js тесты
- Линтеры (flake8, eslint)
- Форматирование (black, prettier)
