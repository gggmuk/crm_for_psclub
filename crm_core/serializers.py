from rest_framework import serializers
from .models import Place, Session, Tariff, Promotion, Booking
from loyalty.models import Client

class ClientSerializer(serializers.ModelSerializer):
    referrals_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'telegram_id', 'name', 'rank', 'bonus_points', 'total_hours_played', 'referral_code', 'referrals_count']

    def get_referrals_count(self, obj):
        # аннотируется в list-view, fallback — count()
        return getattr(obj, '_referrals_count', None) if getattr(obj, '_referrals_count', None) is not None else obj.referrals.count()


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ['id', 'name', 'hourly_rate', 'description', 'is_active']

    def validate_hourly_rate(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной.")
        return value


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'description', 'discount_percentage', 'is_active']

    def validate_discount_percentage(self, value):
        if value is None or not (0 <= value <= 90):
            raise serializers.ValidationError("Скидка должна быть от 0 до 90%.")
        return value

class PlaceSerializer(serializers.ModelSerializer):
    active_session = serializers.SerializerMethodField()
    current_session_id = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    tariff_info = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ['id', 'name', 'status', 'place_type', 'active_session', 'current_session_id', 'client_name', 'tariff_info']

    def _session_map(self):
        # Кэшируем активные сессии одним запросом для всего списка (без N+1)
        if not hasattr(self, '_cached_map'):
            places = self.context.get('places_qs', None)
            if places is not None:
                place_ids = [p.id for p in places]
            else:
                # fallback: один объект
                obj = self.context.get('single_place')
                place_ids = [obj.id] if obj else []
            sessions = Session.objects.filter(
                place_id__in=place_ids, status='active'
            ).select_related('client', 'place')
            self._cached_map = {s.place_id: s for s in sessions}
        return self._cached_map

    def _get_session(self, obj):
        # Быстрый путь для single-object без контекста
        cached = getattr(self, '_cached_map', None)
        if cached is not None:
            return cached.get(obj.id)
        if obj.status != 'occupied':
            return None
        return Session.objects.filter(place=obj, status='active').select_related('client').first()

    def get_active_session(self, obj):
        session = self._get_session(obj)
        if session:
            return {
                'id': session.id,
                'client_name': session.guest_name if session.is_guest else (session.client.name if session.client else 'Гость'),
                'client_id': session.client.id if session.client else None,
                'telegram_id': session.client.telegram_id if session.client else None,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'scheduled_end_time': session.scheduled_end_time,
                'is_guest': session.is_guest,
            }
        return None

    def get_current_session_id(self, obj):
        session = self._get_session(obj)
        return session.id if session else None

    def get_client_name(self, obj):
        session = self._get_session(obj)
        if session:
            return session.guest_name if session.is_guest else (session.client.name if session.client else 'Гость')
        return None

    def get_tariff_info(self, obj):
        if obj.tariff:
            return {
                'name': obj.tariff.name,
                'hourly_rate': float(obj.tariff.hourly_rate),
                'description': obj.tariff.description
            }
        return None

class BookingSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source='place.name', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'place', 'place_name', 'client_name', 'start_time', 'end_time', 'status', 'created_at']

class SessionSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source='place.name', read_only=True)
    client_name = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'place', 'place_name', 'client_name', 'start_time', 'end_time',
            'scheduled_end_time', 'status', 'cost', 'is_guest', 'guest_name',
            'discount_applied', 'duration_minutes'
        ]

    def get_client_name(self, obj):
        if obj.is_guest:
            return obj.guest_name or 'Гость'
        return obj.client.name if obj.client else 'Неизвестный'

    def get_duration_minutes(self, obj):
        if obj.end_time and obj.start_time:
            delta = obj.end_time - obj.start_time
            return round(delta.total_seconds() / 60, 1)
        return None
