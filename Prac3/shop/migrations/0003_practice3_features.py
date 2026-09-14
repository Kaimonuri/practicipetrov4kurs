from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def normalize_old_statuses(apps, schema_editor):
    Order = apps.get_model('shop', 'Order')
    Order.objects.filter(status='Shipped').update(status='Processing')
    Order.objects.filter(status='Canceled').update(status='New')


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shop', '0002_part2_features'),
    ]

    operations = [
        migrations.RunPython(normalize_old_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('New', 'Новый'),
                    ('Processing', 'В обработке'),
                    ('Completed', 'Завершено'),
                ],
                default='New',
                max_length=20,
                verbose_name='Статус',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_method',
            field=models.CharField(
                choices=[
                    ('courier', 'Курьерская доставка'),
                    ('pickup', 'Самовывоз'),
                ],
                default='courier',
                max_length=20,
                verbose_name='Способ доставки',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_date',
            field=models.DateField(blank=True, null=True, verbose_name='Желаемая дата доставки'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('on_receipt', 'При получении'),
                    ('sbp', 'Перевод по СБП'),
                ],
                default='on_receipt',
                max_length=20,
                verbose_name='Способ оплаты',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='coupon_code',
            field=models.CharField(blank=True, max_length=50, verbose_name='Промокод'),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='Скидка',
            ),
        ),
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='Код')),
                ('discount_type', models.CharField(choices=[('percent', 'Процентная скидка'), ('fixed', 'Фиксированная скидка')], max_length=10, verbose_name='Тип скидки')),
                ('value', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='Размер скидки')),
                ('active', models.BooleanField(default=True, verbose_name='Активен')),
                ('valid_from', models.DateTimeField(blank=True, null=True, verbose_name='Действует с')),
                ('valid_until', models.DateTimeField(blank=True, null=True, verbose_name='Действует до')),
            ],
            options={
                'verbose_name': 'Промокод',
                'verbose_name_plural': 'Промокоды',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='WishlistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Добавлен')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlisted_by', to='shop.product', verbose_name='Товар')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlist_items', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Избранный товар',
                'verbose_name_plural': 'Избранное',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='wishlistitem',
            constraint=models.UniqueConstraint(fields=('user', 'product'), name='unique_wishlist_product_per_user'),
        ),
    ]
