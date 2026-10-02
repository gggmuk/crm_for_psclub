# 🎮 CRM PlayStation Club API Documentation

## Base URL

```
http://localhost:8000/api
```

## Authentication

API использует Token Authentication или заголовок `X-API-Key` для менеджерских эндпоинтов.

---

## Endpoints

### 👤 Клиенты

#### Получить информацию о клиенте

```http
GET /api/client_info/<telegram_id>/
```

**Response:**
```json
{
  "id": 1,
  "name": "Иван Иванов",
  "rank": "Постоянный",
  "bonus_points": 150,
  "total_hours_played": 25.5,
  "referral_code": "IVAN2024",
  "referred_by": null
}
```

#### Регистрация клиента

```http
POST /api/register_client/
```

**Body:**
```json
{
  "telegram_id": 123456789,
  "name": "Иван Иванов"
}
```

#### Список клиентов

```http
GET /api/clients/
```

**Query Parameters:**
- `page` — номер страницы
- `page_size` — количество на странице

---

### 🎮 Места и сессии

#### Статус мест

```http
GET /api/place_status/
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "VIP Room 1",
    "status": "free",
    "place_type": "VIP",
    "tariff_info": {
      "name": "VIP",
      "hourly_rate": 500.0
    }
  }
]
```

#### Начать сессию

```http
POST /api/start_session/
```

**Body:**
```json
{
  "place_id": 1,
  "telegram_id": 123456789,
  "client_name": "Иван Иванов",
  "is_guest": false,
  "duration": 60,
  "promotion_id": 1
}
```

#### Остановить сессию

```http
POST /api/stop_session/<session_id>/
```

#### Продлить сессию

```http
POST /api/prolong_session/
```

**Body:**
```json
{
  "session_id": 1,
  "minutes_to_add": 30
}
```

---

### 📅 Бронирования

#### Создать бронирование

```http
POST /api/create_booking/
```

**Body:**
```json
{
  "client_id": 1,
  "place_id": 1,
  "start_time": "2024-01-15T14:00:00Z",
  "end_time": "2024-01-15T16:00:00Z"
}
```

#### Мои бронирования

```http
GET /api/my_bookings/<telegram_id>/
```

#### Отменить бронирование

```http
PATCH /api/cancel_booking/<booking_id>/
```

---

### 👥 Рефералы

#### Применить реферальный код

```http
POST /api/apply_referral/
```

**Body:**
```json
{
  "telegram_id": 123456789,
  "referral_code": "IVAN2024"
}
```

#### Статистика рефералов

```http
GET /api/referral_stats/<telegram_id>/
```

---

### 💰 Тарифы и акции

#### Список тарифов

```http
GET /api/tariffs/
```

#### Создать тариф

```http
POST /api/tariffs/manage/
```

#### Обновить тариф

```http
PUT /api/tariffs/<id>/
```

#### Удалить тариф

```http
DELETE /api/tariffs/<id>/
```

#### Список акций

```http
GET /api/promotions/
```

#### Создать акцию

```http
POST /api/promotions/
```

---

### 📊 Статистика

#### Статистика менеджера

```http
GET /api/manager_stats/
```

**Response:**
```json
{
  "total_revenue_day": 15000.0,
  "occupancy_rate_current": 75.0,
  "avg_session_cost": 450.0,
  "top_performing_place_name": "VIP Room 1"
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно |
| 201 | Создано |
| 400 | Неверный запрос |
| 401 | Не авторизован |
| 403 | Запрещено |
| 404 | Не найдено |
| 500 | Внутренняя ошибка сервера |

---

## Примеры использования

### Python

```python
import requests

# Получить статус мест
response = requests.get('http://localhost:8000/api/place_status/')
places = response.json()

# Начать сессию
data = {
    'place_id': 1,
    'telegram_id': 123456789,
    'duration': 60
}
response = requests.post('http://localhost:8000/api/start_session/', json=data)
```

### JavaScript

```javascript
// Получить статус мест
const response = await fetch('http://localhost:8000/api/place_status/');
const places = await response.json();

// Начать сессию
const response = await fetch('http://localhost:8000/api/start_session/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    place_id: 1,
    telegram_id: 123456789,
    duration: 60
  })
});
```

---

## 🔐 Безопасность

- Все запросы должны содержать заголовок `Authorization: Token <token>` или `X-API-Key: <key>`
- Используйте HTTPS в production
- Ограничьте частоту запросов (rate limiting 120/мин)
