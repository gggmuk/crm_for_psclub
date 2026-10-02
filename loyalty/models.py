import uuid
from django.db import models

RANK_CHOICES = [
    ('Новичок', 'Новичок'),
    ('Постоянный', 'Постоянный'),
    ('VIP', 'VIP'),
    ('Легенда', 'Легенда'),
]

class Client(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID", db_index=True)
    name = models.CharField(max_length=255, verbose_name="Имя")
    rank = models.CharField(max_length=100, verbose_name="Ранг", default='Новичок', choices=RANK_CHOICES)
    bonus_points = models.IntegerField(default=0, verbose_name="Бонусные баллы")
    total_hours_played = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Всего часов игры"
    )
    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True, verbose_name="Реферальный код")
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals', verbose_name="Пригласил")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата регистрации")

    def save(self, *args, **kwargs):
        if not self.referral_code:
            # retry при коллизии unique
            for _ in range(5):
                candidate = str(uuid.uuid4())[:8].upper()
                if not type(self).objects.filter(referral_code=candidate).exists():
                    self.referral_code = candidate
                    break
            if not self.referral_code:
                self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.telegram_id})"

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        indexes = [
            models.Index(fields=['referral_code']),
        ]
