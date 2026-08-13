from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Event

User = get_user_model()

# The default STORAGES config uses a manifest-based static files storage
# (see config/settings.py) that requires `collectstatic` to have run. Tests
# that render full pages need the plain storage instead.
_STORAGES_WITHOUT_MANIFEST = {
    **settings.STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def create_user(username, is_active=True, is_staff=False):
    return User.objects.create_user(
        username=username,
        password="clave-segura-123",
        street="Calle Principal",
        house_number="1",
        is_active=is_active,
        is_staff=is_staff,
    )


@override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
class CalendarViewTests(TestCase):
    def test_unauthenticated_user_is_redirected_to_login(self):
        response = self.client.get(reverse("calendario"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('calendario')}",
        )

    def test_inactive_user_cannot_access(self):
        # ModelBackend re-validates is_active on every request (not just at
        # login), so even a forced session for an inactive user is treated
        # as anonymous and redirected to login.
        user = create_user("inactivo", is_active=False)
        self.client.force_login(user)
        response = self.client.get(reverse("calendario"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('calendario')}",
        )

    def test_active_user_sees_the_calendar(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")
        response = self.client.get(reverse("calendario"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "calendario/calendario.html")


class EventListViewTests(TestCase):
    def setUp(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("calendario-eventos"))
        self.assertEqual(response.status_code, 401)

    def test_returns_events_within_requested_range(self):
        Event.objects.create(
            title="Dentro del rango",
            description="desc",
            location="cancha",
            start_at=datetime(2026, 3, 15, 18, 0, tzinfo=UTC),
        )
        Event.objects.create(
            title="Fuera del rango",
            start_at=datetime(2026, 4, 15, 18, 0, tzinfo=UTC),
        )

        response = self.client.get(
            reverse("calendario-eventos"),
            {"start": "2026-03-01T00:00:00Z", "end": "2026-04-01T00:00:00Z"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Dentro del rango")
        self.assertEqual(
            data[0]["extendedProps"]["location"],
            "cancha",
        )

    def test_no_params_uses_current_month(self):
        now = timezone.now()
        Event.objects.create(title="Este mes", start_at=now)
        if now.month == 12:
            other_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            other_month = now.replace(month=now.month + 1, day=1)
        Event.objects.create(title="Otro mes", start_at=other_month)

        response = self.client.get(reverse("calendario-eventos"))

        self.assertEqual(response.status_code, 200)
        titles = [event["title"] for event in response.json()]
        self.assertIn("Este mes", titles)
        self.assertNotIn("Otro mes", titles)
