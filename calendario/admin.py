from django.contrib import admin

from .models import Confirmation, Event


class ConfirmationInline(admin.TabularInline):
    """Read-only attendance-confirmation history for a user, shown inline
    on their own admin page. Existing rows can be deleted (an admin can
    correct the record when someone confirmed but didn't attend), but
    nothing here is editable and no new rows can be added through this
    inline i.e. this view is not a way to fabricate confirmations."""

    model = Confirmation
    fk_name = "user"
    verbose_name = "confirmación de asistencia"
    verbose_name_plural = "confirmaciones de asistencia"
    extra = 0
    fields = ("event", "event_date", "confirmed_at")
    readonly_fields = ("event", "event_date", "confirmed_at")

    @admin.display(description="fecha del evento")
    def event_date(self, obj):
        return obj.event.start_at

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "start_at",
        "end_at",
        "location",
        "created_by",
    )
    list_filter = ("start_at",)
    search_fields = ("title", "description", "location")


@admin.register(Confirmation)
class ConfirmationAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "confirmed_at")
    list_filter = ("event",)
    search_fields = ("user__username", "event__title")
