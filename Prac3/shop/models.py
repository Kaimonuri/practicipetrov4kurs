from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE, verbose_name='Категория')
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True)
    image = models.ImageField(
        upload_to='products/%Y/%m/%d',
        blank=True,
        verbose_name='Изображение',
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    stock = models.PositiveIntegerField(verbose_name='Остаток')
    available = models.BooleanField(default=True, verbose_name='Доступен')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


class Coupon(models.Model):
    TYPE_PERCENT = 'percent'
    TYPE_FIXED = 'fixed'
    DISCOUNT_TYPES = [
        (TYPE_PERCENT, 'Процентная скидка'),
        (TYPE_FIXED, 'Фиксированная скидка'),
    ]

    code = models.CharField('Код', max_length=50, unique=True)
    discount_type = models.CharField('Тип скидки', max_length=10, choices=DISCOUNT_TYPES)
    value = models.DecimalField(
        'Размер скидки',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    active = models.BooleanField('Активен', default=True)
    valid_from = models.DateTimeField('Действует с', null=True, blank=True)
    valid_until = models.DateTimeField('Действует до', null=True, blank=True)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['code']

    def __str__(self):
        return self.code

    def clean(self):
        if self.discount_type == self.TYPE_PERCENT and self.value > 100:
            raise ValidationError({'value': 'Процентная скидка не может быть больше 100%.'})
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValidationError({'valid_until': 'Дата окончания должна быть позже даты начала.'})

    def is_valid(self):
        now = timezone.now()
        if not self.active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def calculate_discount(self, subtotal):
        subtotal = Decimal(subtotal)
        if self.discount_type == self.TYPE_PERCENT:
            discount = subtotal * self.value / Decimal('100')
        else:
            discount = self.value
        return min(discount, subtotal).quantize(Decimal('0.01'))


class Order(models.Model):
    STATUS_CHOICES = [
        ('New', 'Новый'),
        ('Processing', 'В обработке'),
        ('Completed', 'Завершено'),
    ]
    DELIVERY_CHOICES = [
        ('courier', 'Курьерская доставка'),
        ('pickup', 'Самовывоз'),
    ]
    PAYMENT_CHOICES = [
        ('on_receipt', 'При получении'),
        ('sbp', 'Перевод по СБП'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Пользователь',
    )
    first_name = models.CharField('Имя', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    email = models.EmailField('Email')
    address = models.CharField('Адрес', max_length=250)
    postal_code = models.CharField('Индекс', max_length=20)
    city = models.CharField('Город', max_length=100)
    delivery_method = models.CharField(
        'Способ доставки', max_length=20, choices=DELIVERY_CHOICES, default='courier'
    )
    delivery_date = models.DateField('Желаемая дата доставки', null=True, blank=True)
    payment_method = models.CharField(
        'Способ оплаты', max_length=20, choices=PAYMENT_CHOICES, default='on_receipt'
    )
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='New')
    paid = models.BooleanField('Оплачен', default=False)
    coupon_code = models.CharField('Промокод', max_length=50, blank=True)
    discount_amount = models.DecimalField(
        'Скидка', max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    created = models.DateTimeField('Создан', auto_now_add=True)
    updated = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        ordering = ['-created']
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ №{self.id}'

    def get_subtotal_cost(self):
        return sum((item.get_cost() for item in self.items.all()), Decimal('0.00'))

    def get_total_cost(self):
        return max(self.get_subtotal_cost() - self.discount_amount, Decimal('0.00'))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE, verbose_name='Товар')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.product} × {self.quantity}'

    def get_cost(self):
        return self.price * self.quantity


class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE, verbose_name='Товар')
    user = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE, verbose_name='Пользователь')
    rating = models.PositiveSmallIntegerField(
        'Рейтинг', validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField('Комментарий')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'user'],
                name='unique_product_review_per_user',
            )
        ]
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return f'{self.product} - {self.user} ({self.rating})'


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items', verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by', verbose_name='Товар')
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_wishlist_product_per_user')
        ]
        ordering = ['-created_at']
        verbose_name = 'Избранный товар'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user}: {self.product}'
