from django.contrib import admin

from shop.admin_site import lab_admin_site
from .models import Profile


@admin.register(Profile, site=lab_admin_site)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone']
    search_fields = ['user__username', 'full_name', 'phone']
