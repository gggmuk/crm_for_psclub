# Деплой в production

## 1. Переменные окружения
Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Пример | Обязательно |
|---|---|---|
| `DJANGO_SECRET_KEY` | длинная случайная строка 50+ символов | да |
| `DJANGO_DEBUG` | `False` | да |
| `DJANGO_ALLOWED_HOSTS` | `your-backend.com` | да |
| `BOT_TOKEN` | токен от @BotFather | да |
| `CRM_API_KEY` | случайные 32+ символов | да |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | да |
| `CORS_ALLOWED_ORIGINS` | `https://your-frontend.com` | если есть фронт |
| `CSRF_TRUSTED_ORIGINS` | `https://your-backend.com` | да |
| `DATABASE_URL` | `postgres://user:pass@host:5432/db` | для Postgres |
| `SENTRY_DSN` | `https://...@sentry.io/...` | нет |

Без `DATABASE_URL` работает SQLite (только для старта, настройте бэкапы).

## 2. Backend (любой хостинг: Railway / Render / VPS)
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
```
Проверка: `GET /health/` → `{"status":"ok"}`.

`Dockerfile.backend` и `docker-compose.yml` уже настроены под это
(gunicorn + migrate при старте + healthcheck).

## 3. Telegram-бот (тот же сервер)
```bash
cd tg_bot && npm install
# tg_bot/.env: BOT_TOKEN, CRM_API_KEY, API_BASE_URL=https://your-backend.com/api
node index.js
```
В compose бот ждет `backend` по healthcheck и стартует сам.

## 4. После запуска
1. Войдите в `/admin/` под superuser — дашборды `/dashboard/`, `/super/` требуют staff.
2. Создайте тарифы/места, проверьте `/api/place_status/`.
3. Напишите боту `/start`, создайте бронь, подтвердите в дашборде.
4. SQLite: `python manage.py backup_db --keep 7` по cron (папка `backups/`).

## 5. Чек-лист безопасности
- [ ] Старый токен отозван, новый только в `.env`
- [ ] `DEBUG=False`, `ALLOWED_HOSTS` без `*`
- [ ] CORS ограничен своими доменами, HTTPS включен
- [ ] Роли: операторы — staff, тарифы/аналитика — superuser
