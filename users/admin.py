from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Provider", {"fields": ("provider",)}),
    )
    list_display = DjangoUserAdmin.list_display + ("provider",)
