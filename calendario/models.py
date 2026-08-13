from django.conf import settings
from django.db import models


class Evento(models.Model):
    """A single calendar occurrence. Recurring events are stored as one row
    per occurrence, sharing a `grupo_recurrente` so they can be managed as a
    series without coupling their individual fields."""

    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    ubicacion = models.CharField("ubicación", max_length=200, blank=True)
    fecha_inicio = models.DateTimeField("fecha y hora de inicio")
    fecha_fin = models.DateTimeField(
        "fecha y hora de fin", null=True, blank=True
    )
    grupo_recurrente = models.UUIDField(
        "grupo recurrente", null=True, blank=True, db_index=True
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_creados",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ("fecha_inicio",)

    def __str__(self):
        return self.titulo


class Confirmacion(models.Model):
    """A resident's confirmed attendance to an Evento."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="confirmaciones",
    )
    evento = models.ForeignKey(
        Evento,
        verbose_name="evento",
        on_delete=models.CASCADE,
        related_name="confirmaciones",
    )
    confirmado_en = models.DateTimeField("confirmado en", auto_now_add=True)

    class Meta:
        verbose_name = "confirmación"
        verbose_name_plural = "confirmaciones"
        ordering = ("evento__fecha_inicio",)
        constraints = (
            models.UniqueConstraint(
                fields=("usuario", "evento"),
                name="unica_confirmacion_por_usuario_y_evento",
            ),
        )

    def __str__(self):
        return f"{self.usuario} → {self.evento}"
