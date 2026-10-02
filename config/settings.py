import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent

if _DOTENV_AVAILABLE:
    load_dotenv(BASE_DIR / '.env')


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(name: str, default: str = '') -> list:
    raw = os.getenv(name, default)
    if not raw:
        return []
    return [x.strip() for x in raw.split(',') if x.strip()]


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = _env_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', '*')
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*'] if DEBUG else ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'crm_core',
    'loyalty',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# Prod: задайте DATABASE_URL=postgres://user:pass@host:5432/dbname
if os.getenv('DATABASE_URL'):
    try:
        import dj_database_url as _dj
        DATABASES['default'] = _dj.parse(os.getenv('DATABASE_URL'), conn_max_age=600)
    except ImportError:
        pass

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Secrets (никогда не хардкодить) ---
TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN', '')
# Общий секрет для связки backend <-> tg_bot / mini_app / dashboard-JS.
# Бот и Mini App шлют его в заголовке X-API-Key для менеджерских ручек.
CRM_API_KEY = os.getenv('CRM_API_KEY', '')

# --- CORS / CSRF ---
if _env_bool('CORS_ALLOW_ALL_ORIGINS', DEBUG):
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = _env_list(
        'CORS_ALLOWED_ORIGINS',
        '',
    )

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
]

CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', '')

# --- DRF: троттлинг + пагинация ---
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',
        'user': '300/min',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# --- Prod hardening ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# Sentry (опционально): задайте SENTRY_DSN в prod
if os.getenv('SENTRY_DSN'):
    try:
        import sentry_sdk as _sentry
        _sentry.init(
            dsn=os.getenv('SENTRY_DSN'),
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_RATE', '0.1')),
            send_default_pii=False,
        )
    except ImportError:
        pass

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
