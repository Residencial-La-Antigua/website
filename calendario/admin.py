from django.contrib import admin

from .models import Confirmation, Event


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
