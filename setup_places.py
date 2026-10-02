import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from crm_core.models import Place, Tariff

def setup():
    print("Deleting existing places...")
    Place.objects.all().delete()
    
    places_config = [
        ('VIP', 'VIP Room 1'),
        ('VIP', 'VIP Room 2'),
        ('Basic', 'Basic PC 1'),
        ('Basic', 'Basic PC 2'),
        ('Bootcamp', 'Bootcamp 1'),
        ('Bootcamp', 'Bootcamp 2'),
    ]
    
    print("Creating new places...")
    for p_type, name in places_config:
        place = Place.objects.create(
            name=name,
            place_type=p_type,
            status='free'
        )
        print(f"Created {place.name} [{place.place_type}]")
        
    print(f"Total places: {Place.objects.count()}")

if __name__ == '__main__':
    setup()
