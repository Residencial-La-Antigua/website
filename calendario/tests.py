from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Confirmation, Event

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


class EventCreateViewTests(TestCase):
    def test_requires_authentication(self):
        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {"title": "Jornada", "start_at": "2026-08-20T09:00"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Event.objects.count(), 0)

    def test_requires_staff(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {"title": "Jornada", "start_at": "2026-08-20T09:00"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Event.objects.count(), 0)

    def test_staff_can_create_event_with_required_fields_only(self):
        admin = create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {"title": "Jornada de siembra", "start_at": "2026-08-20T09:00"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get()
        self.assertEqual(event.title, "Jornada de siembra")
        self.assertEqual(event.created_by, admin)
        self.assertEqual(response.json()["title"], "Jornada de siembra")

    def test_staff_can_create_event_with_all_fields(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Jornada de siembra",
                "description": "Traer guantes",
                "location": "Calle Jade",
                "start_at": "2026-08-20T09:00",
                "end_at": "2026-08-20T11:00",
            },
        )

        self.assertEqual(response.status_code, 201)
        event = Event.objects.get()
        self.assertEqual(event.description, "Traer guantes")
        self.assertEqual(event.location, "Calle Jade")
        self.assertIsNotNone(event.end_at)

    def test_missing_required_field_returns_errors_without_creating(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"), {"description": "Sin título"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)
        errors = response.json()["errors"]
        self.assertIn("title", errors)
        self.assertIn("start_at", errors)


class EventUpdateViewTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Jornada de siembra",
            location="Parque central",
            start_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        )

    def update_url(self):
        return reverse("calendario-eventos-editar", args=[self.event.pk])

    def test_requires_authentication(self):
        response = self.client.post(
            self.update_url(),
            {"title": "Cambiado", "start_at": "2026-08-20T09:00"},
        )
        self.assertEqual(response.status_code, 401)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Jornada de siembra")

    def test_requires_staff(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.post(
            self.update_url(),
            {"title": "Cambiado", "start_at": "2026-08-20T09:00"},
        )

        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Jornada de siembra")

    def test_staff_can_edit_event(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            self.update_url(),
            {
                "title": "Jornada de siembra (reprogramada)",
                "location": "Cancha",
                "start_at": "2026-08-21T10:00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Jornada de siembra (reprogramada)")
        self.assertEqual(self.event.location, "Cancha")
        self.assertEqual(response.json()["title"], self.event.title)

    def test_edit_only_affects_this_event(self):
        other_event = Event.objects.create(
            title="Otro evento",
            start_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        )
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        self.client.post(
            self.update_url(),
            {"title": "Cambiado", "start_at": "2026-08-20T09:00"},
        )

        other_event.refresh_from_db()
        self.assertEqual(other_event.title, "Otro evento")

    def test_missing_required_field_returns_errors_without_changing(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(self.update_url(), {"location": "Cancha"})

        self.assertEqual(response.status_code, 400)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Jornada de siembra")
        self.assertEqual(self.event.location, "Parque central")

    def test_editing_nonexistent_event_returns_404(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-editar", args=[self.event.pk + 999]),
            {"title": "Cambiado", "start_at": "2026-08-20T09:00"},
        )

        self.assertEqual(response.status_code, 404)


class EventDeleteViewTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Jornada de siembra",
            start_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        )

    def delete_url(self):
        return reverse("calendario-eventos-eliminar", args=[self.event.pk])

    def test_requires_authentication(self):
        response = self.client.delete(self.delete_url())
        self.assertEqual(response.status_code, 401)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_requires_staff(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.delete(self.delete_url())

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_staff_can_delete_event(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.delete(self.delete_url())

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())

    def test_deleting_event_cascades_confirmations(self):
        resident = create_user("residente")
        Confirmation.objects.create(user=resident, event=self.event)
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.delete(self.delete_url())

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Confirmation.objects.count(), 0)

    def test_deleting_nonexistent_event_returns_404(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.delete(
            reverse("calendario-eventos-eliminar", args=[self.event.pk + 999])
        )

        self.assertEqual(response.status_code, 404)
