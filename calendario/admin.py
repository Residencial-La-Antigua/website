from django.contrib import admin

from .models import Confirmacion, Evento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "fecha_inicio",
        "fecha_fin",
        "ubicacion",
        "creado_por",
    )
    list_filter = ("fecha_inicio",)
    search_fields = ("titulo", "descripcion", "ubicacion")


@admin.register(Confirmacion)
class ConfirmacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "evento", "confirmado_en")
    list_filter = ("evento",)
    search_fields = ("usuario__username", "evento__titulo")
