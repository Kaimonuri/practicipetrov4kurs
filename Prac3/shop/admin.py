from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from .admin_site import lab_admin_site
from .models import Category, Coupon, Order, OrderItem, Product, Review, WishlistItem


try:
    lab_admin_site.register(User, UserAdmin)
    lab_admin_site.register(Group, GroupAdmin)
except admin.sites.AlreadyRegistered:
    pass


@admin.register(Category, site=lab_admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product, site=lab_admin_site)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'available']
    list_filter = ['available', 'category', 'created', 'updated']
    list_editable = ['price', 'stock', 'available']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.action(description='Статус: Новый')
def mark_new(modeladmin, request, queryset):
    queryset.update(status='New')


@admin.action(description='Статус: В обработке')
def mark_processing(modeladmin, request, queryset):
    queryset.update(status='Processing')


@admin.action(description='Статус: Завершено')
def mark_completed(modeladmin, request, queryset):
    queryset.update(status='Completed')


@admin.action(description='Отметить как оплаченные')
def mark_paid(modeladmin, request, queryset):
    queryset.update(paid=True)


@admin.register(Order, site=lab_admin_site)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = 'admin/shop/order/change_list.html'
    list_display = [
        'id',
        'customer_name',
        'email',
        'delivery_method',
        'payment_method',
        'delivery_date',
        'paid',
        'status',
        'created',
    ]
    list_filter = ['status', 'paid', 'delivery_method', 'payment_method', 'delivery_date', 'created']
    search_fields = ['first_name', 'last_name', 'email', 'address', 'coupon_code']
    list_select_related = ['user']
    inlines = [OrderItemInline]
    actions = [mark_new, mark_processing, mark_completed, mark_paid]

    @admin.display(description='Клиент')
    def customer_name(self, obj):
        return f'{obj.last_name} {obj.first_name}'.strip()


@admin.register(Review, site=lab_admin_site)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']


@admin.register(Coupon, site=lab_admin_site)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'value', 'active', 'valid_from', 'valid_until']
    list_filter = ['discount_type', 'active']
    search_fields = ['code']


@admin.register(WishlistItem, site=lab_admin_site)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']
