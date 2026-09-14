from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Product


def clear_catalog_cache():
    cache.delete_many(['catalog_categories', 'catalog_products'])


@receiver([post_save, post_delete], sender=Product)
def product_changed(**kwargs):
    clear_catalog_cache()


@receiver([post_save, post_delete], sender=Category)
def category_changed(**kwargs):
    clear_catalog_cache()
