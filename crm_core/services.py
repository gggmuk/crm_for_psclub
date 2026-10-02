from django.db import transaction
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from .models import Session, Place, Promotion
from datetime import timedelta
import math
import logging

logger = logging.getLogger(__name__)


def send_telegram_notification(client_id, message, background: bool = True):
    """Прокси в loyalty.services, чтобы не дублировать токен и логику."""
    try:
        from loyalty.services import send_telegram_notification as _send
        return _send(client_id, message, background=background)
    except Exception as e:  # pragma: no cover - страховка от циклических импортов
        logger.error(f"Error sending notification: {e}")
        return False

@transaction.atomic
def start_session(client, place, is_guest=False, guest_name=None, duration_minutes=None, promotion_id=None):
    """
    Начинает новую сессию для клиента или гостя на указанном месте.
    
    Args:
        client: Client object (может быть None для гостей)
        place: Place object
        is_guest: bool - является ли сессия гостевой
        guest_name: str - имя гостя (опционально)
        duration_minutes: int - длительность сессии в минутах (опционально)
        promotion_id: int - ID акции (опционально)
    """
    # Блокируем выбранное место для избежания состояния гонки
    place = Place.objects.select_for_update().get(pk=place.pk)

    if place.status != 'free':
        raise ValueError(f"Место {place.name} не свободно (статус: {place.status})")

    start_time = timezone.now()
    scheduled_end_time = None
    if duration_minutes:
        scheduled_end_time = start_time + timedelta(minutes=int(duration_minutes))

    # Handle Promotion
    promotion = None
    discount_percentage = 0
    if promotion_id:
        try:
            promotion = Promotion.objects.get(pk=promotion_id, is_active=True)
            discount_percentage = promotion.discount_percentage
        except Promotion.DoesNotExist:
            pass # Ignore invalid promotion IDs

    # Создаем новую сессию
    session = Session.objects.create(
        client=client if not is_guest else None,
        place=place,
        start_time=start_time,
        scheduled_end_time=scheduled_end_time,
        status='active',
        cost=0,
        is_guest=is_guest,
        guest_name=guest_name if is_guest else None,
        promotion=promotion,
        discount_applied=discount_percentage
    )

    # Обновляем статус места
    place.status = 'occupied'
    place.save()

    # Напоминание за 10 минут до конца (только с длительностью, в фоне)
    if duration_minutes and not is_guest:
        try:
            _schedule_end_reminder(session.id, duration_minutes)
        except Exception:
            pass

    return session

@transaction.atomic
def stop_session(session_id, notify: bool = True):
    """
    Завершает активную сессию, рассчитывает стоимость и обновляет статистику клиента.
    notify=False — тихо (для auto_close пачкой), уведомление уходит в фоне.
    """
    try:
        session = Session.objects.select_for_update().get(pk=session_id)
    except Session.DoesNotExist:
        raise ValueError(f"Сессия с ID {session_id} не найдена")

    if session.status == 'completed':
        raise ValueError("Сессия уже завершена")

    # 1. Устанавливаем время окончания
    now = timezone.now()
    session.end_time = now

    # 2. Рассчитываем длительность и стоимость
    duration = session.end_time - session.start_time
    hours_played_exact = Decimal(duration.total_seconds()) / Decimal(3600)
    
    hours_to_charge = Decimal(math.ceil(hours_played_exact))
    if hours_to_charge == 0:
        hours_to_charge = Decimal(1)  # Минимальная оплата за час

    # Используем тариф места или дефолтную цену
    if session.place.tariff:
        hourly_rate = session.place.tariff.hourly_rate
    else:
        hourly_rate = Decimal(300)  # Дефолтная цена
        
    cost = hours_to_charge * hourly_rate
    
    # Apply Discount
    if session.discount_applied > 0:
        discount_factor = Decimal(1) - (Decimal(session.discount_applied) / Decimal(100))
        cost = cost * discount_factor

    session.cost = cost
    session.status = 'completed'

    # 3. Освобождаем место
    place = session.place
    place.status = 'free'
    place.save()

    session.save()

    bonus_points_added = 0
    client = session.client

    # 4. Обновляем статистику клиента (только для зарегистрированных)
    if not session.is_guest and client:
        client.total_hours_played += hours_played_exact

        # Начисление бонусов (1%)
        bonus_points_added = int(cost * Decimal(0.01))
        client.bonus_points += bonus_points_added
        client.save(update_fields=['total_hours_played', 'bonus_points'])

        # 5. Отправка уведомления в фоне (только для зарегистрированных)
        if notify:
            try:
                msg = (
                    f"✅ *Сессия завершена*\n"
                    f"📍 Место: {place.name}\n"
                    f"💰 Стоимость: {cost}₽\n"
                    f"🎁 Начислено бонусов: {bonus_points_added}\n"
                    f"💳 Ваш баланс: {client.bonus_points}"
                )
                send_telegram_notification(client.id, msg, background=True)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")

    return {
        "session": session,
        "cost": cost,
        "bonus_points_added": bonus_points_added,
        "client": client
    }


def _schedule_end_reminder(session_id, duration_minutes):
    """Напоминание за 10 минут до конца сессии (daemon-поток, для портфолио-демо)."""
    try:
        import threading as _th
        if not duration_minutes or int(duration_minutes) <= 15:
            return
        delay = int(duration_minutes) * 60 - 10 * 60

        def _remind():
            try:
                s = Session.objects.select_related('client', 'place').filter(pk=session_id, status='active').first()
                if not s or s.is_guest or not s.client:
                    return
                send_telegram_notification(
                    s.client.id,
                    f"⏳ *Напоминание*\n📍 {s.place.name}: осталось ~10 минут.",
                    background=True,
                )
            except Exception as e:
                logger.error(f"Reminder failed for session {session_id}: {e}")

        t = _th.Timer(delay, _remind)
        t.daemon = True
        t.start()
    except Exception as e:
        logger.error(f"Failed to schedule reminder: {e}")


def auto_close_expired_sessions(limit: int = 50):
    """
    Закрывает активные сессии с истекшим scheduled_end_time.
    Уведомления отправляются в фоне, обработка батчем чтобы не вешать API.
    """
    now = timezone.now()
    expired_ids = list(
        Session.objects.filter(
            status='active',
            scheduled_end_time__lte=now
        ).values_list('id', flat=True)[:limit]
    )

    count = 0
    for session_id in expired_ids:
        try:
            stop_session(session_id, notify=True)
            count += 1
            logger.info(f"Auto-closed expired session {session_id}")
        except Exception as e:
            logger.error(f"Failed to auto-close session {session_id}: {e}")

    return count


def auto_close_expired_bookings(limit: int = 100):
    """Просроченные pending → canceled (no-show), confirmed в прошлом → completed."""
    from .models import Booking

    now = timezone.now()
    expired = list(
        Booking.objects.filter(
            status__in=['pending', 'confirmed'], end_time__lte=now
        ).values_list('id', 'status')[:limit]
    )
    canceled = completed = 0
    for booking_id, st in expired:
        try:
            if st == 'pending':
                Booking.objects.filter(pk=booking_id, status='pending').update(status='canceled')
                canceled += 1
            else:
                Booking.objects.filter(pk=booking_id, status='confirmed').update(status='completed')
                completed += 1
        except Exception as e:
            logger.error(f"Failed to auto-close booking {booking_id}: {e}")
    return {'canceled': canceled, 'completed': completed}
