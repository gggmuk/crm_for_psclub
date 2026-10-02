from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class Tariff(models.Model):
    """Тарифный план для игровых мест"""
    name = models.CharField(max_length=100, verbose_name="Название тарифа")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за час (₽)", validators=[MinValueValidator(0)])
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"{self.name} - {self.hourly_rate}₽/час"
    
    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ['hourly_rate']


class Promotion(models.Model):
    """Акции и спецпредложения"""
    name = models.CharField(max_length=100, verbose_name="Название акции")
    description = models.TextField(verbose_name="Описание")
    discount_percentage = models.PositiveIntegerField(default=0, verbose_name="Скидка (%)", validators=[MinValueValidator(0), MaxValueValidator(90)])
    is_active = models.BooleanField(default=True, verbose_name="Активна", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"{self.name} (-{self.discount_percentage}%)"

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ['-created_at']


class Place(models.Model):
    STATUS_CHOICES = [
        ('free', 'Свободно'),
        ('occupied', 'Занято'),
        ('maintenance', 'Обслуживание'),
    ]

    name = models.CharField(max_length=255, verbose_name="Название места")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='free', 
        verbose_name="Статус"
    )
    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='places',
        verbose_name="Тариф"
    )
    
    PLACE_TYPES = [
        ('VIP', 'VIP'),
        ('Basic', 'Basic'),
        ('Bootcamp', 'Bootcamp'),
    ]
    place_type = models.CharField(
        max_length=20,
        choices=PLACE_TYPES,
        default='Basic',
        verbose_name="Тип места",
        db_index=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Место"
        verbose_name_plural = "Места"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['place_type']),
        ]


class Session(models.Model):
    client = models.ForeignKey(
        'loyalty.Client', 
        on_delete=models.CASCADE, 
        related_name='sessions',
        verbose_name="Клиент",
        null=True,
        blank=True  # Теперь клиент опционален для гостевых сессий
    )
    place = models.ForeignKey(
        Place, 
        on_delete=models.CASCADE, 
        related_name='sessions',
        verbose_name="Место"
    )
    guest_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Имя гостя"
    )
    start_time = models.DateTimeField(verbose_name="Начало сессии")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Конец сессии")
    scheduled_end_time = models.DateTimeField(null=True, blank=True, verbose_name="Запланированное окончание")
    
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('canceled', 'Отменена'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active', 
        verbose_name="Статус"
    )
    
    cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Стоимость (₽)"
    )
    
    is_guest = models.BooleanField(default=False, verbose_name="Гостевая сессия")

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Примененная акция"
    )
    
    discount_applied = models.PositiveIntegerField(
        default=0,
        verbose_name="Примененная скидка (%)"
    )

    def __str__(self):
        return f"Сессия {self.id} - {self.place.name}"

    class Meta:
        verbose_name = "Сессия"
        verbose_name_plural = "Сессии"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['status', 'scheduled_end_time']),
            models.Index(fields=['place', 'status']),
        ]


class Booking(models.Model):
    """Бронирование мест"""
    client = models.ForeignKey(
        'loyalty.Client',
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Клиент"
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Место"
    )
    start_time = models.DateTimeField(verbose_name="Начало брони")
    end_time = models.DateTimeField(verbose_name="Конец брони")
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('canceled', 'Отменено'),
        ('completed', 'Завершено'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Бронь {self.id} - {self.client.name} на {self.start_time}"

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['place', 'status', 'start_time']),
        ]
