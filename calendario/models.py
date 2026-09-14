from django.conf import settings
from django.db import models

from .validators import validate_meeting_link_domain


class Event(models.Model):
    """A single calendar occurrence. Recurring events are stored as one row
    per occurrence, sharing a `recurring_group` so they can be managed as a
    series without coupling their individual fields."""

    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción", blank=True)
    location = models.CharField("ubicación", max_length=200, blank=True)
    meeting_link = models.URLField(
        "enlace de reunión virtual",
        blank=True,
        validators=[validate_meeting_link_domain],
    )
    start_at = models.DateTimeField("fecha y hora de inicio")
    end_at = models.DateTimeField("fecha y hora de fin", null=True, blank=True)
    recurring_group = models.UUIDField(
        "grupo recurrente", null=True, blank=True, db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_events",
    )
    created_at = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ("start_at",)

    def __str__(self):
        return self.title


class Confirmation(models.Model):
    """A resident's confirmed attendance to an Event."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="confirmations",
    )
    event = models.ForeignKey(
        Event,
        verbose_name="evento",
        on_delete=models.CASCADE,
        related_name="confirmations",
    )
    confirmed_at = models.DateTimeField("confirmado en", auto_now_add=True)

    class Meta:
        verbose_name = "confirmación"
        verbose_name_plural = "confirmaciones"
        ordering = ("event__start_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("user", "event"),
                name="unique_confirmation_per_user_and_event",
            ),
        )

    def __str__(self):
        return f"{self.user} → {self.event}"
