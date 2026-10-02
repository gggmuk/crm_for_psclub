# 🏗 Архитектура проекта Gaming Club

## 📊 Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛИ                          │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐        ┌──────────┐
    │   Web    │         │ Telegram │        │          │
    │ Browser  │         │   Bot    │        │          │
    └──────────┘         └──────────┘        └──────────┘
           │                    │                    │
           │                    │                    │
           └────────────────────┼────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Django REST API     │
                    │   (Backend Server)    │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   SQLite Database     │
                    └───────────────────────┘
```

## 🔄 Поток данных

### 1. Web Dashboard Flow

```
Менеджер → Browser → Django Views → Templates → HTML Response
                          ↓
                    REST API (для динамики)
                          ↓
                      Database
```

### 2. Telegram Bot Flow

```
Пользователь → Telegram → Bot (Node.js) → Django API → Database
                                                ↓
                                          Response
                                                ↓
                                        Telegram Message
```

### 3. Mini App Flow

```
Пользователь → Telegram Mini App (React) → Django API → Database
                                                  ↓
                                            JSON Response
                                                  ↓
                                          UI Update (React)
```

## 📁 Структура файлов

```
вкр/
│
├── 📂 config/                    # Django конфигурация
│   ├── settings.py              # Настройки проекта
│   ├── urls.py                  # URL маршруты
│   └── wsgi.py                  # WSGI конфигурация
│
├── 📂 crm_core/                 # Основная бизнес-логика
│   ├── models.py                # Модели: Place, Session, Booking, Tariff, Promotion
│   ├── views.py                 # API endpoints
│   ├── serializers.py           # DRF сериализаторы
│   ├── services.py              # Бизнес-логика (расчеты, автозакрытие)
│   └── migrations/              # Миграции БД
│
├── 📂 loyalty/                  # Система лояльности
│   ├── models.py                # Модель Client (с рефералами)
│   ├── views.py                 # API для клиентов и рефералов
│   ├── serializers.py           # Сериализаторы клиентов
│   └── services.py              # Логика начисления бонусов
│
├── 📂 templates/                # HTML шаблоны
│   ├── landing.html             # Главная страница
│   ├── operations_dashboard.html # Операционный дашборд
│   └── super_dashboard.html     # Супер-дашборд (аналитика)
│
├── 📂 static/                   # Статические файлы
│   └── css/                     # Стили
│
├── 📂 tg_bot/                   # Telegram бот (Node.js)
│   ├── index.js                 # Основной файл бота
│   ├── package.json             # Node.js зависимости
│   ├── .env                     # Переменные окружения (BOT_TOKEN)
│   └── node_modules/            # Установленные пакеты
│
│   ├── src/
│   │   ├── components/          # React компоненты
│   │   │   ├── BottomNav.jsx    # Нижняя навигация
│   │   │   └── BookingModal.jsx # Модальное окно бронирования
│   │   ├── pages/               # Страницы приложения
│   │   │   ├── HomePage.jsx     # Главная (список мест)
│   │   │   ├── ProfilePage.jsx  # Профиль пользователя
│   │   │   ├── ReferralsPage.jsx # Рефералы
│   │   │   └── BookingsPage.jsx # Бронирования
│   │   ├── lib/
│   │   │   └── api.js           # API клиент (axios)
│   │   ├── App.jsx              # Главный компонент
│   │   └── index.css            # Глобальные стили
│   ├── public/                  # Публичные файлы
│   ├── package.json             # Зависимости
│   ├── vite.config.js           # Vite конфигурация
│   ├── firebase.json            # Firebase Hosting конфигурация
│   └── DEPLOY.md                # Инструкция по деплою
│
├── 📄 db.sqlite3                # База данных SQLite
├── 📄 manage.py                 # Django управление
├── 📄 requirements.txt          # Python зависимости
├── 📄 start_all.bat             # Скрипт запуска всех сервисов
├── 📄 README.md                 # Главная документация
└── 📄 QUICKSTART.md             # Быстрый старт
```

## 🗄️ Модели данных

### Client (Клиент)

```python
- id: Integer (PK)
- telegram_id: BigInteger (Unique)
- name: String
- rank: String (Новичок, Опытный, Мастер...)
- bonus_points: Integer
- total_hours_played: Decimal
- referral_code: String (Unique, автогенерация)
- referred_by: ForeignKey(self) - кто пригласил
```

### Place (Игровое место)

```python
- id: Integer (PK)
- name: String
- status: Choice (free/occupied/maintenance)
- place_type: Choice (VIP/Basic/Bootcamp)
- tariff: ForeignKey(Tariff)
```

### Session (Игровая сессия)

```python
- id: Integer (PK)
- client: ForeignKey(Client, nullable)
- place: ForeignKey(Place)
- guest_name: String (для гостей)
- start_time: DateTime
- end_time: DateTime (nullable)
- scheduled_end_time: DateTime (nullable)
- status: Choice (active/completed/canceled)
- cost: Decimal
- is_guest: Boolean
- promotion: ForeignKey(Promotion, nullable)
- discount_applied: Integer
```

### Booking (Бронирование)

```python
- id: Integer (PK)
- client: ForeignKey(Client)
- place: ForeignKey(Place)
- start_time: DateTime
- end_time: DateTime
- status: Choice (pending/confirmed/canceled/completed)
- created_at: DateTime
```

### Tariff (Тариф)

```python
- id: Integer (PK)
- name: String
- hourly_rate: Decimal
- description: Text
- is_active: Boolean
- created_at: DateTime
```

### Promotion (Акция)

```python
- id: Integer (PK)
- name: String
- description: Text
- discount_percentage: Integer
- is_active: Boolean
- created_at: DateTime
```

## 🔌 API Endpoints

### Клиенты

- `GET /api/client_info/<telegram_id>/` - Получить инфо о клиенте
- `POST /api/register_client/` - Зарегистрировать клиента
- `GET /api/clients/` - Список всех клиентов

### Места и сессии

- `GET /api/place_status/` - Статус всех мест
- `POST /api/start_session/` - Начать сессию
- `POST /api/stop_session/<session_id>/` - Завершить сессию
- `POST /api/prolong_session/` - Продлить сессию

### Бронирования

- `POST /api/create_booking/` - Создать бронь
- `GET /api/my_bookings/<telegram_id>/` - Мои бронирования
- `PATCH /api/cancel_booking/<booking_id>/` - Отменить бронь

### Рефералы

- `POST /api/apply_referral/` - Применить реферальный код
- `GET /api/referral_stats/<telegram_id>/` - Статистика рефералов

### Управление

- `GET /api/tariffs/` - Список тарифов
- `POST /api/tariffs/manage/` - Создать тариф
- `PUT /api/tariffs/<id>/` - Обновить тариф
- `DELETE /api/tariffs/<id>/` - Удалить тариф
- `GET /api/promotions/` - Список акций
- `POST /api/promotions/` - Создать акцию
- `PUT /api/promotions/<id>/` - Обновить акцию
- `DELETE /api/promotions/<id>/` - Удалить акцию
- `GET /api/manager_stats/` - Статистика менеджера

## 🔐 Безопасность

### Текущая конфигурация (Development)

- ✅ CORS: Разрешены все источники
- ✅ CSRF: Отключен для API
- ⚠️ DEBUG: True
- ⚠️ SECRET_KEY: Тестовый ключ

### Для Production

- 🔒 CORS: Только Firebase домен
- 🔒 CSRF: Включен
- 🔒 DEBUG: False
- 🔒 SECRET_KEY: Уникальный секретный ключ
- 🔒 HTTPS: Обязательно
- 🔒 Database: PostgreSQL вместо SQLite

## 🚀 Деплой стратегия

### Backend (Django)

Рекомендуемые платформы:

- **Railway** (бесплатный tier)
- **Render** (бесплатный tier)
- **PythonAnywhere** (бесплатный tier)
- **Heroku** (платный)

### Mini App (удалено, пока не подключено к боту)

- **Firebase Hosting** ✅ (рекомендуется)
- **Vercel**
- **Netlify**
- **GitHub Pages**

### Telegram Bot

- Запускать на том же сервере, что и Backend
- Или использовать **Railway/Render** отдельно

## 📊 Производительность

### Оптимизации

- ✅ Автозакрытие истекших сессий
- ✅ Кеширование статуса мест
- ✅ Индексы на telegram_id
- ✅ Lazy loading в React

### Масштабирование

- Переход на PostgreSQL
- Redis для кеширования
- CDN для статики
- Load balancer для API

## 🎯 Roadmap

### Фаза 1 (Текущая) ✅

- ✅ Web дашборды
- ✅ Telegram бот
- ⏸ Mini App (удалено)
- ✅ Базовая аналитика

### Фаза 2 (Планируется)

- 📱 Мобильное приложение (Flutter)
- 💳 Интеграция платежей
- 📧 Email уведомления
- 📊 Расширенная аналитика
- 🎮 Интеграция с играми

### Фаза 3 (Будущее)

- 🤖 AI рекомендации
- 🏆 Турниры и лиги
- 🎁 Магазин бонусов
- 📱 Push уведомления
