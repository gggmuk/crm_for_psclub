from rest_framework import serializers
from .models import Client

class ClientSerializer(serializers.ModelSerializer):
    referrals_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['telegram_id', 'name', 'rank', 'bonus_points', 'total_hours_played', 'referral_code', 'referrals_count']

    def get_referrals_count(self, obj):
        return obj.referrals.count()
