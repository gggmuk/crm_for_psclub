from django.db import transaction
from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from loyalty.models import Client
from .models import Booking, Place, Promotion, Session, Tariff
from .permissions import IsAdminOrService, IsManagerOrService, IsManagerReadServiceWrite
from .serializers import (
    BookingSerializer,
    ClientSerializer,
    PlaceSerializer,
    PromotionSerializer,
    SessionSerializer,
    TariffSerializer,
)
from .services import (
    auto_close_expired_bookings,
    auto_close_expired_sessions,
    start_session,
    stop_session as stop_session_service,
)


def _parse_booking_dt(value):
    """Парсит ISO-строку, naive считаем UTC чтобы не ловить naive/aware mismatch."""
    if not value:
        return None
    if hasattr(value, 'year'):
        dt = value
    else:
        dt = parse_datetime(str(value))
        if dt is None:
            return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


@api_view(['POST'])
@permission_classes([IsManagerOrService])
def start_session_api(request):
    telegram_id = request.data.get('telegram_id') or request.data.get('client_telegram_id') or request.data.get('client_id')
    place_id = request.data.get('place_id')
    client_name = (request.data.get('client_name') or '').strip()
    guest_name = (request.data.get('guest_name') or '').strip()
    is_guest = request.data.get('is_guest', False)
    promotion_id = request.data.get('promotion_id')
    raw_duration = request.data.get('duration')

    if not place_id:
        return Response({"error": "place_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    duration_minutes = None
    if raw_duration not in (None, '', 0, '0'):
        try:
            duration_minutes = int(raw_duration)
            if not 1 <= duration_minutes <= 1440:
                return Response({"error": "duration must be 1..1440 minutes"}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError):
            return Response({"error": "duration must be integer minutes"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        place = get_object_or_404(Place, pk=place_id)

        if is_guest or (guest_name and not telegram_id):
            if not guest_name:
                return Response({"error": "guest_name is required for guest sessions"}, status=status.HTTP_400_BAD_REQUEST)
            session = start_session(
                client=None, place=place, is_guest=True, guest_name=guest_name,
                duration_minutes=duration_minutes, promotion_id=promotion_id,
            )
            return Response({
                "session_id": session.id, "status": session.status,
                "place": session.place.name, "guest_name": guest_name,
                "is_guest": True, "start_time": session.start_time,
            }, status=status.HTTP_201_CREATED)

        if not telegram_id:
            return Response({"error": "telegram_id or guest_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Client.objects.get(telegram_id=telegram_id)
        except Client.DoesNotExist:
            if not client_name:
                return Response({"error": "client_name is required for new clients"}, status=status.HTTP_400_BAD_REQUEST)
            client = Client.objects.create(
                telegram_id=telegram_id, name=client_name, rank='Новичок',
                bonus_points=0, total_hours_played=0,
            )

        session = start_session(client, place, duration_minutes=duration_minutes, promotion_id=promotion_id)
        return Response({
            "session_id": session.id, "status": session.status,
            "place": session.place.name,
            "client": session.client.name if session.client else None,
            "client_created": client.id, "start_time": session.start_time,
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsManagerOrService])
def stop_session(request, session_id):
    try:
        result = stop_session_service(session_id)
        session = result['session']
        client = result['client']
        return Response({
            "session_id": session.id,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "cost": result['cost'],
            "client": {
                "name": client.name if client else (session.guest_name or "Гость"),
                "telegram_id": client.telegram_id if client else None,
                "bonus_points_added": result['bonus_points_added'],
                "current_bonus_points": client.bonus_points if client else 0,
                "total_hours_played": round(float(client.total_hours_played), 2) if client else 0,
            },
        }, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def place_status_list(request):
    auto_close_expired_sessions()
    auto_close_expired_bookings()
    places = list(Place.objects.select_related('tariff').all().order_by('id'))
    serializer = PlaceSerializer(places, many=True, context={'places_qs': places})
    # Прогреваем кэш активных сессий одним запросом
    active = Session.objects.filter(place_id__in=[p.id for p in places], status='active').select_related('client')
    session_map = {s.place_id: s for s in active}
    serializer._cached_map = session_map
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsManagerOrService])
def prolong_session(request):
    from datetime import timedelta

    session_id = request.data.get('session_id')
    minutes_to_add = request.data.get('minutes_to_add')
    if not session_id or not minutes_to_add:
        return Response({"error": "session_id and minutes_to_add are required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        minutes_to_add = int(minutes_to_add)
        if not 1 <= minutes_to_add <= 1440:
            return Response({"error": "minutes_to_add must be 1..1440"}, status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError):
        return Response({"error": "minutes_to_add must be integer"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = get_object_or_404(Session, pk=session_id)
        if session.status != 'active':
            return Response({"error": "Session is not active"}, status=status.HTTP_400_BAD_REQUEST)
        if session.scheduled_end_time:
            session.scheduled_end_time += timedelta(minutes=minutes_to_add)
        else:
            session.scheduled_end_time = timezone.now() + timedelta(minutes=minutes_to_add)
        session.save(update_fields=['scheduled_end_time'])
        return Response({
            "session_id": session.id, "status": "prolonged",
            "minutes_added": minutes_to_add,
            "projected_end_time": session.scheduled_end_time,
            "message": f"Session extended by {minutes_to_add} minutes",
        }, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def manager_stats(request):
    from datetime import timedelta
    from decimal import Decimal

    now = timezone.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_sessions = Session.objects.filter(start_time__gte=day_start)

    total_revenue = daily_sessions.filter(status='completed').aggregate(total=Sum('cost'))['total'] or Decimal(0)
    avg_cost = daily_sessions.filter(status='completed').aggregate(avg=Avg('cost'))['avg'] or Decimal(0)

    total_places = Place.objects.count()
    seconds_since_start = (now - day_start).total_seconds()
    total_duration_seconds = 0
    for session in daily_sessions.only('start_time', 'end_time'):
        if session.end_time:
            duration = (session.end_time - session.start_time).total_seconds()
        else:
            duration = (now - session.start_time).total_seconds()
        if duration > 0:
            total_duration_seconds += duration

    if total_places > 0 and seconds_since_start > 1:
        max_possible_seconds = total_places * seconds_since_start
        occupancy_rate = min((total_duration_seconds / max_possible_seconds) * 100, 100.0)
    else:
        occupancy_rate = 0

    top_place = daily_sessions.filter(status='completed').values('place__name').annotate(
        revenue=Sum('cost')).order_by('-revenue').first()
    top_place_name = top_place['place__name'] if top_place else "N/A"

    return Response({
        "total_revenue_day": float(total_revenue),
        "occupancy_rate_current": round(occupancy_rate, 1),
        "avg_session_cost": float(avg_cost),
        "top_performing_place_name": top_place_name,
        "total_sessions_today": daily_sessions.count(),
        "active_sessions": daily_sessions.filter(status='active').count(),
        "completed_sessions": daily_sessions.filter(status='completed').count(),
    })


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def clients_list(request):
    q = (request.GET.get('q') or request.GET.get('search') or '').strip()
    limit = request.GET.get('limit')
    try:
        limit = min(int(limit), 500) if limit else 200
    except (TypeError, ValueError):
        limit = 200
    qs = Client.objects.all().order_by('-id')
    if q:
        if q.lstrip('-').isdigit():
            qs = qs.filter(Q(name__icontains=q) | Q(telegram_id=int(q)))
        else:
            qs = qs.filter(name__icontains=q)
    qs = qs.prefetch_related('referrals')[:limit]
    # аннотация для сериализатора без N+1
    for c in qs:
        c._referrals_count = c.referrals.count()
    serializer = ClientSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def tariffs_list(request):
    tariffs = Tariff.objects.filter(is_active=True).order_by('hourly_rate')
    return Response([{
        'id': t.id, 'name': t.name, 'hourly_rate': float(t.hourly_rate),
        'description': t.description,
    } for t in tariffs])


@api_view(['POST'])
@permission_classes([IsAdminOrService])
def manage_tariffs(request):
    serializer = TariffSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdminOrService])
def tariff_detail(request, pk):
    tariff = get_object_or_404(Tariff, pk=pk)
    if request.method == 'PUT':
        serializer = TariffSerializer(tariff, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    tariff.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsManagerReadServiceWrite])
def manage_promotions(request):
    if request.method == 'GET':
        promotions = Promotion.objects.all().order_by('-created_at')
        serializer = PromotionSerializer(promotions, many=True)
        return Response(serializer.data)
    # POST — только superuser или сервис
    user = getattr(request, 'user', None)
    is_admin = bool(user and user.is_authenticated and user.is_superuser)
    if not is_admin:
        from django.conf import settings as _s
        provided = request.headers.get('X-API-Key', '')
        if not (getattr(_s, 'CRM_API_KEY', '') and provided == _s.CRM_API_KEY):
            return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    serializer = PromotionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdminOrService])
def promotion_detail(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)
    if request.method == 'PUT':
        serializer = PromotionSerializer(promotion, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    promotion.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def create_booking_api(request):
    telegram_id = request.data.get('telegram_id')
    place_id = request.data.get('place_id')
    start_time = _parse_booking_dt(request.data.get('start_time'))
    end_time = _parse_booking_dt(request.data.get('end_time'))

    if not all([telegram_id, place_id, start_time, end_time]):
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    if end_time <= start_time:
        return Response({"error": "end_time must be after start_time"}, status=status.HTTP_400_BAD_REQUEST)
    if end_time - start_time > timezone.timedelta(days=1):
        return Response({"error": "Booking too long (max 24h)"}, status=status.HTTP_400_BAD_REQUEST)

    client = get_object_or_404(Client, telegram_id=telegram_id)
    place = get_object_or_404(Place, pk=place_id)
    if place.status == 'maintenance':
        return Response({"error": "Place is under maintenance"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # Пересечения с бронями (блокируем место на время проверки)
        Place.objects.select_for_update().filter(pk=place.pk).first()
        overlaps = Booking.objects.filter(
            place=place, status__in=['confirmed', 'pending'],
            start_time__lt=end_time, end_time__gt=start_time,
        ).exists()
        if overlaps:
            return Response({"error": "Place is already booked for this time"}, status=status.HTTP_400_BAD_REQUEST)

        # Пересечения с активными сессиями
        now = timezone.now()
        active_sessions = Session.objects.filter(place=place, status='active')
        for s in active_sessions:
            s_end = s.scheduled_end_time or (s.start_time + timezone.timedelta(hours=12))
            if s.start_time < end_time and s_end > start_time:
                # Будущая бронь после конца текущей сессии — ок, иначе конфликт
                if start_time < s_end and not (start_time >= s_end):
                    # если сессия открытая и бронь сильно в будущем (>2ч) — разрешаем
                    if s.scheduled_end_time is None and start_time > now + timezone.timedelta(hours=2):
                        continue
                    return Response(
                        {"error": "Place is occupied by active session in this time"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        booking = Booking.objects.create(
            client=client, place=place, start_time=start_time, end_time=end_time, status='pending',
        )

    serializer = BookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def my_bookings_api(request, telegram_id):
    client = get_object_or_404(Client, telegram_id=telegram_id)
    bookings = Booking.objects.filter(client=client).select_related('place').order_by('-start_time')[:100]
    serializer = BookingSerializer(bookings, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
def cancel_booking_api(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.status in ['canceled', 'completed']:
        return Response({"error": "Cannot cancel this booking"}, status=status.HTTP_400_BAD_REQUEST)
    booking.status = 'canceled'
    booking.save(update_fields=['status'])
    return Response({"message": "Booking canceled successfully"}, status=status.HTTP_200_OK)


# ============ ANALYTICS ============

@api_view(['GET'])
@permission_classes([IsManagerOrService])
def analytics_revenue(request):
    from datetime import timedelta
    from decimal import Decimal

    now = timezone.now()
    start_30 = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Один запрос вместо 30
    rows = (
        Session.objects.filter(status='completed', end_time__gte=start_30)
        .annotate(day=TruncDate('end_time'))
        .values('day')
        .annotate(total=Sum('cost'), cnt=Count('id'))
    )
    by_day = {}
    for r in rows:
        key = r['day'].strftime('%Y-%m-%d') if hasattr(r['day'], 'strftime') else str(r['day'])
        by_day[key] = (float(r['total'] or 0), r['cnt'])

    daily_data = []
    for i in range(29, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        key = day_start.strftime('%Y-%m-%d')
        revenue, cnt = by_day.get(key, (0.0, 0))
        daily_data.append({
            'date': key, 'day_label': day_start.strftime('%d.%m'),
            'revenue': revenue, 'sessions_count': cnt,
        })

    revenue_by_type = Session.objects.filter(status='completed').values('place__place_type').annotate(
        total_revenue=Sum('cost'), total_sessions=Count('id'), avg_cost=Avg('cost')).order_by('-total_revenue')
    type_data = [{
        'place_type': item['place__place_type'] or 'Unknown',
        'total_revenue': float(item['total_revenue'] or 0),
        'total_sessions': item['total_sessions'],
        'avg_cost': float(item['avg_cost'] or 0),
    } for item in revenue_by_type]

    revenue_by_tariff = Session.objects.filter(status='completed', place__tariff__isnull=False).values(
        'place__tariff__name').annotate(total_revenue=Sum('cost'), total_sessions=Count('id')).order_by('-total_revenue')
    tariff_data = [{
        'tariff_name': item['place__tariff__name'],
        'total_revenue': float(item['total_revenue'] or 0),
        'total_sessions': item['total_sessions'],
    } for item in revenue_by_tariff]

    all_time = Session.objects.filter(status='completed').aggregate(
        total_revenue=Sum('cost'), total_sessions=Count('id'), avg_session_cost=Avg('cost'))

    return Response({
        'daily': daily_data, 'by_place_type': type_data, 'by_tariff': tariff_data,
        'all_time': {
            'total_revenue': float(all_time['total_revenue'] or 0),
            'total_sessions': all_time['total_sessions'] or 0,
            'avg_session_cost': float(all_time['avg_session_cost'] or 0),
        },
    })


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def analytics_occupancy(request):
    from datetime import timedelta

    now = timezone.now()
    total_places = Place.objects.count() or 1

    # Один запрос за 7 дней вместо 24*7
    week_ago = now - timedelta(days=7)
    sessions = list(
        Session.objects.filter(
            Q(start_time__lt=now) & (Q(end_time__isnull=True) | Q(end_time__gt=week_ago))
        ).only('start_time', 'end_time')
    )

    hourly_data = []
    for hour in range(24):
        total_occupancy = 0
        days_counted = 0
        for day_offset in range(7):
            day = now - timedelta(days=day_offset)
            hour_start = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            if hour_end > now:
                continue
            occupied_seconds = 0
            for s in sessions:
                s_end = s.end_time or now
                if s.start_time < hour_end and s_end > hour_start:
                    overlap_start = max(s.start_time, hour_start)
                    overlap_end = min(s_end, hour_end)
                    if overlap_end > overlap_start:
                        occupied_seconds += (overlap_end - overlap_start).total_seconds()
            max_seconds = total_places * 3600
            occupancy_pct = min((occupied_seconds / max_seconds) * 100, 100) if max_seconds > 0 else 0
            total_occupancy += occupancy_pct
            days_counted += 1
        avg_occupancy = total_occupancy / days_counted if days_counted > 0 else 0
        hourly_data.append({'hour': hour, 'label': f'{hour:02d}:00', 'avg_occupancy': round(avg_occupancy, 1)})

    active_places = Place.objects.filter(status='occupied').count()
    current_occupancy = round((active_places / total_places) * 100, 1) if total_places > 0 else 0

    type_stats = []
    for place_type, type_label in Place.PLACE_TYPES:
        total_of_type = Place.objects.filter(place_type=place_type).count()
        occupied_of_type = Place.objects.filter(place_type=place_type, status='occupied').count()
        pct = round((occupied_of_type / total_of_type) * 100, 1) if total_of_type > 0 else 0
        type_stats.append({
            'type': place_type, 'label': type_label, 'total': total_of_type,
            'occupied': occupied_of_type, 'occupancy_pct': pct,
        })

    return Response({
        'hourly_heatmap': hourly_data, 'current_occupancy': current_occupancy,
        'active_places': active_places, 'total_places': total_places, 'by_type': type_stats,
    })


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def analytics_clients(request):
    top_by_revenue = Session.objects.filter(status='completed', client__isnull=False).values(
        'client__name', 'client__telegram_id', 'client__rank', 'client__bonus_points').annotate(
        total_spent=Sum('cost'), total_sessions=Count('id')).order_by('-total_spent')[:10]
    top_clients = [{
        'name': c['client__name'], 'telegram_id': c['client__telegram_id'],
        'rank': c['client__rank'], 'bonus_points': c['client__bonus_points'],
        'total_spent': float(c['total_spent'] or 0), 'total_sessions': c['total_sessions'],
    } for c in top_by_revenue]

    rank_dist = Client.objects.values('rank').annotate(count=Count('id')).order_by('-count')
    return Response({
        'top_clients': top_clients,
        'rank_distribution': [{'rank': r['rank'], 'count': r['count']} for r in rank_dist],
        'total_clients': Client.objects.count(),
        'clients_with_referrals': Client.objects.filter(referrals__isnull=False).distinct().count(),
        'avg_bonus_points': round(float(Client.objects.aggregate(avg=Avg('bonus_points'))['avg'] or 0), 0),
    })


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def analytics_sessions(request):
    recent_sessions = Session.objects.filter(status='completed').select_related('place', 'client').order_by('-end_time')[:20]
    serializer = SessionSerializer(recent_sessions, many=True)

    completed = Session.objects.filter(status='completed', end_time__isnull=False).only('start_time', 'end_time')[:500]
    durations = []
    for s in completed:
        try:
            d = (s.end_time - s.start_time).total_seconds() / 60
            if 0 <= d <= 24 * 60:
                durations.append(d)
        except Exception:
            continue
    avg_duration = sum(durations) / len(durations) if durations else 0

    buckets = {'< 30 мин': 0, '30-60 мин': 0, '1-2 часа': 0, '2-3 часа': 0, '3-5 часов': 0, '> 5 часов': 0}
    for d in durations:
        if d < 30:
            buckets['< 30 мин'] += 1
        elif d < 60:
            buckets['30-60 мин'] += 1
        elif d < 120:
            buckets['1-2 часа'] += 1
        elif d < 180:
            buckets['2-3 часа'] += 1
        elif d < 300:
            buckets['3-5 часов'] += 1
        else:
            buckets['> 5 часов'] += 1

    total_completed = Session.objects.filter(status='completed').count()
    guest_sessions = Session.objects.filter(status='completed', is_guest=True).count()
    return Response({
        'recent_sessions': serializer.data,
        'avg_duration_minutes': round(avg_duration, 1),
        'duration_distribution': [{'label': k, 'count': v} for k, v in buckets.items()],
        'guest_sessions': guest_sessions,
        'registered_sessions': total_completed - guest_sessions,
        'total_completed': total_completed,
    })


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def analytics_bookings(request):
    from datetime import timedelta

    now = timezone.now()
    total_bookings = Booking.objects.count()
    pending = Booking.objects.filter(status='pending').count()
    confirmed = Booking.objects.filter(status='confirmed').count()
    canceled = Booking.objects.filter(status='canceled').count()
    completed = Booking.objects.filter(status='completed').count()

    week_ahead = now + timedelta(days=7)
    upcoming = Booking.objects.filter(
        status__in=['pending', 'confirmed'], start_time__gte=now, start_time__lte=week_ahead
    ).select_related('place', 'client').order_by('start_time')[:10]

    popular_places = Booking.objects.values('place__name').annotate(count=Count('id')).order_by('-count')[:5]
    return Response({
        'total_bookings': total_bookings,
        'status_breakdown': {'pending': pending, 'confirmed': confirmed, 'canceled': canceled, 'completed': completed},
        'upcoming': [{
            'id': b.id, 'client_name': b.client.name, 'place_name': b.place.name,
            'start_time': b.start_time, 'end_time': b.end_time, 'status': b.status,
        } for b in upcoming],
        'popular_places': [{'place_name': p['place__name'], 'booking_count': p['count']} for p in popular_places],
    })


@api_view(['POST'])
@permission_classes([IsManagerOrService])
def confirm_booking_api(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.status != 'pending':
        return Response({"error": "Can only confirm pending bookings"}, status=status.HTTP_400_BAD_REQUEST)
    booking.status = 'confirmed'
    booking.save(update_fields=['status'])
    return Response({"message": "Booking confirmed successfully"}, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAdminOrService])
def adjust_bonus_api(request, telegram_id):
    """Ручное начисление/списание бонусов менеджером. {delta: int, reason?: str}"""
    try:
        delta = int(request.data.get('delta', 0))
    except (TypeError, ValueError):
        return Response({"error": "delta must be integer"}, status=status.HTTP_400_BAD_REQUEST)
    if not -10000 <= delta <= 10000:
        return Response({"error": "delta must be -10000..10000"}, status=status.HTTP_400_BAD_REQUEST)
    client = get_object_or_404(Client, telegram_id=telegram_id)
    with transaction.atomic():
        Client.objects.select_for_update().filter(pk=client.pk).first()
        client.bonus_points = F('bonus_points') + delta
        client.save(update_fields=['bonus_points'])
        client.refresh_from_db()
        if client.bonus_points < 0:
            client.bonus_points = 0
            client.save(update_fields=['bonus_points'])
    return Response({
        "telegram_id": client.telegram_id,
        "bonus_points": client.bonus_points,
        "delta": delta,
    })


@api_view(['GET'])
@permission_classes([IsManagerOrService])
def all_bookings_list(request):
    auto_close_expired_bookings()
    status_filter = request.GET.get('status', '').strip()
    bookings = Booking.objects.select_related('place', 'client').order_by('-start_time')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    bookings = bookings[:100]
    return Response([{
        'id': b.id, 'client_name': b.client.name, 'client_telegram_id': b.client.telegram_id,
        'place_name': b.place.name, 'place_id': b.place.id,
        'start_time': b.start_time, 'end_time': b.end_time,
        'status': b.status, 'created_at': b.created_at,
    } for b in bookings])
