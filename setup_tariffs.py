import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from crm_core.models import Place, Tariff, Promotion

print("=== Creating Tariffs ===\n")

# Create tariffs if they don't exist
vip_tariff, created = Tariff.objects.get_or_create(
    name="VIP",
    defaults={
        'hourly_rate': 500,
        'description': 'Premium gaming experience',
        'is_active': True
    }
)
print(f"VIP Tariff: {vip_tariff.hourly_rate} руб/ч {'(created)' if created else '(exists)'}")

basic_tariff, created = Tariff.objects.get_or_create(
    name="Basic",
    defaults={
        'hourly_rate': 200,
        'description': 'Standard gaming',
        'is_active': True
    }
)
print(f"Basic Tariff: {basic_tariff.hourly_rate} руб/ч {'(created)' if created else '(exists)'}")

bootcamp_tariff, created = Tariff.objects.get_or_create(
    name="Bootcamp",
    defaults={
        'hourly_rate': 150,
        'description': 'Budget gaming',
        'is_active': True
    }
)
print(f"Bootcamp Tariff: {bootcamp_tariff.hourly_rate} руб/ч {'(created)' if created else '(exists)'}")

print("\n=== Assigning Tariffs to Places ===\n")

# Assign tariffs to places
places = Place.objects.all()
for place in places:
    if 'VIP' in place.name:
        place.tariff = vip_tariff
        place.save()
        print(f"{place.name} -> VIP Tariff (500 руб/ч)")
    elif 'Basic' in place.name:
        place.tariff = basic_tariff
        place.save()
        print(f"{place.name} -> Basic Tariff (200 руб/ч)")
    elif 'Bootcamp' in place.name:
        place.tariff = bootcamp_tariff
        place.save()
        print(f"{place.name} -> Bootcamp Tariff (150 руб/ч)")

print("\n=== Creating Test Promotion ===\n")

# Create a test promotion
promo, created = Promotion.objects.get_or_create(
    name="Постоянный клиент",
    defaults={
        'discount_percentage': 15,
        'description': 'Скидка 15% для постоянных клиентов',
        'is_active': True
    }
)
print(f"Promotion: {promo.name} - {promo.discount_percentage}% {'(created)' if created else '(exists)'}")

print("\n=== Done! ===")
print("Refresh the dashboard to see the prices!")
