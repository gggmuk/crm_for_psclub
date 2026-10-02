"""Доступ к API: сессия менеджера (staff) ИЛИ общий X-API-Key для бота/Mini App."""
from django.conf import settings
from rest_framework.decorators import permission_classes, api_view, throttle_classes  # noqa: F401 (реэкспорт для views)
from rest_framework.permissions import BasePermission


def _api_key_valid(request) -> bool:
    expected = getattr(settings, 'CRM_API_KEY', '') or ''
    if not expected:
        return False
    provided = request.headers.get('X-API-Key') or request.META.get('HTTP_X_API_KEY', '')
    return bool(provided) and provided == expected


class IsManagerOrService(BasePermission):
    """Пропускает staff-пользователей (дашборд) или запросы с верным X-API-Key (бот)."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            return True
        return _api_key_valid(request)


class IsManagerReadServiceWrite(BasePermission):
    """GET — всем (статусы для бота/мини-аппа), POST/PUT/PATCH/DELETE — только менеджер/сервис."""

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            return True
        return _api_key_valid(request)


class IsAdminOrService(BasePermission):
    """Только superuser (дашборд управления) или сервис с X-API-Key (автоматика)."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and user.is_superuser:
            return True
        return _api_key_valid(request)
