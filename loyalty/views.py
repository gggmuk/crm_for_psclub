from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Client
from .serializers import ClientSerializer

REFERRAL_BONUS = 100


@api_view(['GET'])
def client_info_api(request, telegram_id):
    client = get_object_or_404(Client, telegram_id=telegram_id)
    serializer = ClientSerializer(client)
    return Response(serializer.data)


@api_view(['POST'])
def register_client_api(request):
    telegram_id = request.data.get('telegram_id')
    name = (request.data.get('name') or '').strip()

    if not telegram_id or not name:
        return Response({"error": "telegram_id and name are required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        telegram_id = int(telegram_id)
    except (TypeError, ValueError):
        return Response({"error": "telegram_id must be integer"}, status=status.HTTP_400_BAD_REQUEST)
    if len(name) < 2 or len(name) > 100:
        return Response({"error": "name must be 2..100 chars"}, status=status.HTTP_400_BAD_REQUEST)

    if Client.objects.filter(telegram_id=telegram_id).exists():
        return Response({"error": "Client already exists"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        client = Client.objects.create(
            telegram_id=telegram_id, name=name, rank='Новичок',
            bonus_points=0, total_hours_played=0,
        )
        referral_code = (request.data.get('referral_code') or '').strip().upper()
        if referral_code:
            try:
                referrer = Client.objects.select_for_update().get(referral_code=referral_code)
                if referrer.telegram_id != telegram_id and referrer.id != client.id:
                    client.referred_by = referrer
                    client.save(update_fields=['referred_by'])
                    Client.objects.filter(pk=referrer.pk).update(bonus_points=F('bonus_points') + REFERRAL_BONUS)
            except Client.DoesNotExist:
                pass

    serializer = ClientSerializer(client)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def apply_referral_api(request):
    telegram_id = request.data.get('telegram_id')
    referral_code = (request.data.get('referral_code') or '').strip().upper()

    if not telegram_id or not referral_code:
        return Response({"error": "telegram_id and referral_code are required"}, status=status.HTTP_400_BAD_REQUEST)

    client = get_object_or_404(Client, telegram_id=telegram_id)
    if client.referred_by_id:
        return Response({"error": "Already referred"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        referrer = Client.objects.get(referral_code=referral_code)
    except Client.DoesNotExist:
        return Response({"error": "Invalid referral code"}, status=status.HTTP_404_NOT_FOUND)
    if referrer.id == client.id:
        return Response({"error": "Cannot refer yourself"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        Client.objects.select_for_update().filter(pk=client.pk).first()
        client.referred_by = referrer
        client.save(update_fields=['referred_by'])
        Client.objects.filter(pk=referrer.pk).update(bonus_points=F('bonus_points') + REFERRAL_BONUS)

    return Response({"message": "Referral code applied"}, status=status.HTTP_200_OK)


@api_view(['GET'])
def referral_stats_api(request, telegram_id):
    client = get_object_or_404(Client, telegram_id=telegram_id)
    referrals = client.referrals.all().only('name', 'rank')[:100]
    return Response({
        "referral_code": client.referral_code,
        "referrals_count": client.referrals.count(),
        "referrals": [{"name": r.name, "rank": r.rank} for r in referrals],
    })
