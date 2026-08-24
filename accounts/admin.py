from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from calendario.admin import ConfirmationInline

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "street",
        "house_number",
        "is_active",
        "is_staff",
    )
    list_filter = ("is_active", "is_staff")
    actions = ("approve_users",)
    inlines = (ConfirmationInline,)

    fieldsets = BaseUserAdmin.fieldsets + (  # type: ignore[assignment]
        (
            "Dirección y contacto",
            {"fields": ("street", "house_number", "phone_number")},
        ),
    )

    @admin.action(description="Aprobar cuentas seleccionadas")
    def approve_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} cuenta(s) aprobada(s).")
