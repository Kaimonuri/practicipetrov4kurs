from django.contrib import admin
from .models import Category, Product, Order


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'price',
        'stock',
        'available'
    ]

    list_filter = [
        'available',
        'created',
        'updated'
    ]

    list_editable = [
        'price',
        'stock',
        'available'
    ]

    prepopulated_fields = {
        'slug': ('name',)
    }


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'first_name',
        'last_name',
        'email',
        'city',
        'created'
    ]