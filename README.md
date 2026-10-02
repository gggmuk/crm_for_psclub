# 🎮 CRM PlayStation Club

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python)
![Django](https://img.shields.io/badge/Django-5.2+-092E20?style=flat-square&logo=django)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=nodejs)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram)
![Docker](https://img.shields.io/badge/Docker-24+-2496ED?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions)

**Полноценная CRM-система для PlayStation/компьютерного клуба с Telegram-ботом**

[Установка](#установка) • [Документация](docs/API.md) • [Развёртывание](docs/DEPLOYMENT.md)

</div>

---

## 📋 О проекте

CRM PlayStation Club — это комплексная система управления игровым клубом:

- 🎮 **Web Dashboard** — управление местами, сессиями, тарифами и акциями
- 🤖 **Telegram Bot** — регистрация, бронирование, рефералы, бонусы
- 📊 **Аналитика** — статистика и отчёты
- 🔐 **Безопасность** — env-конфиг, permissions, throttling

---

## 🚀 Установка

### Быстрый старт (Docker)

```bash
git clone https://github.com/gggmuk/crm_for_psclub.git
cd crm_for_psclub
docker-compose up -d
```

### Ручная установка

#### Backend

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Telegram Bot

```bash
cd tg_bot
npm install
cp .env.example .env
# Отредактируйте .env и добавьте BOT_TOKEN
node index.js
```

---

## 📚 Документация

- [API Documentation](docs/API.md) — полное описание REST API
- [Deployment Guide](docs/DEPLOYMENT.md) — руководство по развёртыванию
- [Architecture](ARCHITECTURE.md) — архитектура проекта
- [Changelog](CHANGELOG.md) — история изменений

---

## 🛠️ Технологии

### Backend
- **Django 5.2** — веб-фреймворк
- **Django REST Framework** — REST API
- **SQLite** — база данных (можно заменить на PostgreSQL)

### Telegram Bot
- **Node.js** — среда выполнения
- **node-telegram-bot-api** — Telegram API
- **Axios** — HTTP клиент

### Инфраструктура
- **Docker** — контейнеризация
- **GitHub Actions** — CI/CD

---

## 📊 Структура проекта

```
crm_for_psclub/
├── config/                    # Django конфигурация
├── crm_core/                  # CRM модуль
├── loyalty/                   # Система лояльности
├── templates/                 # HTML шаблоны
├── static/                    # CSS/JS
├── tg_bot/                    # Telegram бот
├── tests/                     # Тесты
├── docs/                      # Документация
├── .github/workflows/         # CI/CD
├── docker-compose.yml         # Docker
├── requirements.txt           # Python зависимости
└── README.md                  # Этот файл
```

---

## ✅ Тестирование

```bash
# Python тесты
python manage.py test

# С покрытием
pytest --cov=. --cov-report=html

# Node.js тесты
cd tg_bot && npm test
```

---

## 🔐 Безопасность

- ✅ CSRF защита
- ✅ CORS настройки
- ✅ Валидация входных данных
- ✅ SQL injection защита (Django ORM)
- ✅ XSS защита
- ✅ Rate limiting (120/мин)
- ✅ Env-конфигурация

---

## 📈 CI/CD

Проект настроен для автоматического тестирования через GitHub Actions:

- ✅ Python тесты (pytest)
- ✅ Node.js тесты
- ✅ Линтеры (flake8, eslint)
- ✅ Форматирование (black, prettier)
- ✅ Проверка миграций

---

## 📊 Модели данных

### Client (Клиент)
- telegram_id, name, rank, bonus_points, total_hours_played, referral_code, referred_by

### Place (Место)
- name, status (free/occupied/maintenance), place_type (VIP/Basic/Bootcamp), tariff

### Session (Сессия)
- client, place, guest_name, start_time, end_time, status, cost, promotion

### Booking (Бронирование)
- client, place, start_time, end_time, status (pending/confirmed/canceled/completed)

### Tariff (Тариф)
- name, hourly_rate, description, is_active

### Promotion (Акция)
- name, description, discount_percentage, is_active

---

## 🤝 Вклад в проект

Мы приветствуем вклад в проект! Пожалуйста, создайте issue или pull request.

---

## 📄 Лицензия

Этот проект лицензирован под MIT License — см. файл [LICENSE](LICENSE) для деталей.

---

## 👨‍💻 Автор

**gggmuk** — разработчик из Кыргызстана

- GitHub: [@gggmuk](https://github.com/gggmuk)

---

<div align="center">

### ⭐ Если тебе нравится проект — поставь звезду!

</div>
