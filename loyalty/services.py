import logging
import threading
import requests
from django.conf import settings
from .models import Client

logger = logging.getLogger(__name__)


def _get_token() -> str:
    return getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''


def _get_api_url() -> str:
    return f"https://api.telegram.org/bot{_get_token()}/sendMessage"


def _post_notification(telegram_id, message) -> bool:
    token = _get_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping notification.")
        return False
    try:
        response = requests.post(
            _get_api_url(),
            json={'chat_id': telegram_id, 'text': message, 'parse_mode': 'Markdown'},
            timeout=5,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message to {telegram_id}: {e}")
        return False


def send_telegram_notification(client_id, message, background: bool = True):
    """Отправка уведомления. По умолчанию — в фоне, чтобы не тормозить API."""
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        logger.error(f"Client with id {client_id} not found.")
        return False

    if not client.telegram_id:
        logger.warning(f"Client {client_id} has no telegram_id.")
        return False

    if background:
        thread = threading.Thread(
            target=_post_notification,
            args=(client.telegram_id, message),
            daemon=True,
        )
        thread.start()
        return True

    return _post_notification(client.telegram_id, message)
