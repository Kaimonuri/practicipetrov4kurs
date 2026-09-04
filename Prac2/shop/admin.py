from django.contrib import admin
from .models import Category, Order, OrderItem, Product, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'available']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'stock', 'available']
    prepopulated_fields = {'slug': ('name',)}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.action(description='Отметить выбранные заказы как оплаченные')
def mark_paid(modeladmin, request, queryset):
    queryset.update(paid=True)


@admin.action(description='Изменить статус выбранных заказов на «Отправлен»')
def mark_shipped(modeladmin, request, queryset):
    queryset.update(status='Shipped')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'paid', 'status', 'created', 'updated']
    list_filter = ['paid', 'status', 'created', 'updated']
    search_fields = ['first_name', 'last_name', 'email', 'address']
    inlines = [OrderItemInline]
    actions = [mark_paid, mark_shipped]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
