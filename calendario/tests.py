import uuid
from datetime import UTC, date, datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .ics import build_event_ics
from .models import Confirmation, Event
from .recurrence import (
    MAX_OCCURRENCES,
    TooManyOccurrences,
    generate_occurrence_starts,
)
from .timezones import to_local_wall_clock, to_true_utc
from .validators import validate_meeting_link_domain
from .views import EventListView

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


class TimezonesTests(TestCase):
    # A fixed offset (no DST) keeps the math unambiguous regardless 
    # of the date used.
    TEST_TZ = dt_timezone(timedelta(hours=3))

    def test_to_true_utc_shifts_by_the_given_timezones_offset(self):
        local = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)
        self.assertEqual(
            to_true_utc(local, tz=self.TEST_TZ),
            datetime(2026, 9, 25, 12, 0, tzinfo=UTC),
        )

    def test_to_true_utc_crosses_a_day_boundary(self):
        local = datetime(2026, 9, 25, 1, 0, tzinfo=UTC)
        self.assertEqual(
            to_true_utc(local, tz=self.TEST_TZ),
            datetime(2026, 9, 24, 22, 0, tzinfo=UTC),
        )

    def test_to_local_wall_clock_is_the_inverse_of_to_true_utc(self):
        original = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)
        converted = to_true_utc(original, tz=self.TEST_TZ)
        self.assertEqual(
            to_local_wall_clock(converted, tz=self.TEST_TZ), original
        )

    def test_defaults_to_resident_tz_when_no_timezone_is_given(self):
        # RESIDENT_TZ (Costa Rica, UTC-6) is the production default -
        # this is the one test that pins that default, so a change to
        # RESIDENT_TZ shows up here rather than silently everywhere.
        local = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)
        self.assertEqual(
            to_true_utc(local), datetime(2026, 9, 25, 21, 0, tzinfo=UTC)
        )


class MeetingLinkValidatorTests(TestCase):
    def test_accepts_exact_allowed_domain(self):
        validate_meeting_link_domain("https://meet.google.com/abc-defg-hij")

    def test_accepts_subdomain_of_allowed_domain(self):
        validate_meeting_link_domain("https://us02web.zoom.us/j/123456789")

    def test_rejects_disallowed_domain(self):
        with self.assertRaises(ValidationError):
            validate_meeting_link_domain("https://example.com/meeting")

    def test_rejects_domain_ending_in_allowed_domain_without_dot_boundary(
        self,
    ):
        # "evilzoom.us" ends with "zoom.us" as a plain string, but isn't a
        # subdomain of it. The check must require a "." boundary, not just
        # a string suffix match.
        with self.assertRaises(ValidationError):
            validate_meeting_link_domain("https://evilzoom.us/j/123")


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

    def test_current_month_range_uses_costa_rica_local_date_not_utc_date(
        self,
    ):
        # 2026-03-01T02:00:00Z is already March 1 in UTC, but still Feb
        # 28 evening in Costa Rica (UTC-6). The "no params" fallback
        # must resolve "today" using the resident-relevant local date,
        # or it picks the wrong month for the first ~6 hours of every
        # UTC day.
        frozen_now = datetime(2026, 3, 1, 2, 0, tzinfo=UTC)
        with patch("calendario.views.timezone.now", return_value=frozen_now):
            start, end = EventListView._current_month_range()

        self.assertEqual(start, datetime(2026, 2, 1, 6, 0, tzinfo=UTC))
        self.assertEqual(end, datetime(2026, 3, 1, 6, 0, tzinfo=UTC))

    def test_confirmed_flag_is_specific_to_the_requesting_user(self):
        event = Event.objects.create(
            title="Café con vecinos", start_at=timezone.now()
        )
        other_resident = create_user("otro_residente")
        Confirmation.objects.create(user=other_resident, event=event)

        response = self.client.get(reverse("calendario-eventos"))

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertFalse(data[0]["extendedProps"]["confirmed"])

    def test_confirmed_count_reflects_all_users_not_just_requesting_user(
        self,
    ):
        event = Event.objects.create(
            title="Café con vecinos", start_at=timezone.now()
        )
        other_resident = create_user("otro_residente")
        Confirmation.objects.create(user=other_resident, event=event)
        Confirmation.objects.create(
            user=User.objects.get(username="residente"), event=event
        )

        response = self.client.get(reverse("calendario-eventos"))

        data = response.json()
        self.assertEqual(data[0]["extendedProps"]["confirmedCount"], 2)


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
        self.assertEqual(response.json()["extendedProps"]["confirmedCount"], 0)

    def test_local_time_round_trips_through_storage_and_serialization(self):
        # A resident types "15:00" meaning 15:00 local time (per RESIDENT_TZ). 
        # The database must store the true UTC equivalent, not 15:00 UTC. 
        # The API response must echo back the original "15:00" the resident typed,
        # since the frontend displays whatever it's given as-is.
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {"title": "Café con vecinos", "start_at": "2026-09-25T15:00"},
        )

        self.assertEqual(response.status_code, 201)
        event = Event.objects.get()
        self.assertEqual(
            event.start_at, datetime(2026, 9, 25, 21, 0, tzinfo=UTC)
        )
        self.assertEqual(response.json()["start"], "2026-09-25T15:00:00+00:00")

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

    def test_staff_can_create_event_with_allowed_meeting_link(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Café virtual",
                "start_at": "2026-08-20T09:00",
                "meeting_link": "https://us02web.zoom.us/j/123456789",
            },
        )

        self.assertEqual(response.status_code, 201)
        event = Event.objects.get()
        self.assertEqual(
            event.meeting_link, "https://us02web.zoom.us/j/123456789"
        )
        self.assertEqual(
            response.json()["extendedProps"]["meetingLink"],
            "https://us02web.zoom.us/j/123456789",
        )

    def test_disallowed_meeting_link_domain_returns_error_without_creating(
        self,
    ):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Café virtual",
                "start_at": "2026-08-20T09:00",
                "meeting_link": "https://example.com/meeting",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)
        self.assertIn("meeting_link", response.json()["errors"])

    def test_recurring_weekly_with_count_creates_one_row_per_occurrence(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Patrullaje",
                "start_at": "2026-08-03T18:00",
                "is_recurring": "on",
                "frequency": "weekly",
                "occurrence_count": "3",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.count(), 3)
        events = list(Event.objects.order_by("start_at"))
        # 18:00 Costa Rica (UTC-6) (per RESIDENT_TZ) is stored as 
        # 00:00 UTC the *next* calendar day.
        self.assertEqual(
            [e.start_at.date().isoformat() for e in events],
            ["2026-08-04", "2026-08-11", "2026-08-18"],
        )
        self.assertEqual(len({e.recurring_group for e in events}), 1)
        self.assertIsNotNone(events[0].recurring_group)
        self.assertEqual(len(response.json()), 3)

    def test_recurring_monthly_with_end_date(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Reunión de junta",
                "start_at": "2026-01-31T18:00",
                "is_recurring": "on",
                "frequency": "monthly",
                "end_date": "2026-05-01",
            },
        )

        self.assertEqual(response.status_code, 201)
        events = list(Event.objects.order_by("start_at"))
        # Jan 31 + 1 month clamps to Feb 28 (2026 is not a leap year), then
        # Mar 31, then Apr 30 (April only has 30 days), then May 31 would
        # exceed the May 1 end_date so it stops. Each is at 18:00 Costa
        # Rica (UTC-6) (per RESIDENT_TZ), stored as 00:00 UTC the *next* 
        # calendar day.
        self.assertEqual(
            [e.start_at.date().isoformat() for e in events],
            ["2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"],
        )

    def test_recurring_preserves_duration_across_occurrences(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Café con vecinos",
                "start_at": "2026-08-03T18:00",
                "end_at": "2026-08-03T19:30",
                "is_recurring": "on",
                "frequency": "weekly",
                "occurrence_count": "2",
            },
        )

        events = list(Event.objects.order_by("start_at"))
        for event in events:
            assert event.end_at is not None
            self.assertEqual(
                event.end_at - event.start_at, timedelta(hours=1, minutes=30)
            )

    def test_recurring_requires_frequency(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Patrullaje",
                "start_at": "2026-08-03T18:00",
                "is_recurring": "on",
                "occurrence_count": "3",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)
        self.assertIn("frequency", response.json()["errors"])

    def test_recurring_rejects_both_end_conditions(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Patrullaje",
                "start_at": "2026-08-03T18:00",
                "is_recurring": "on",
                "frequency": "weekly",
                "occurrence_count": "3",
                "end_date": "2026-09-01",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)

    def test_recurring_rejects_neither_end_condition(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Patrullaje",
                "start_at": "2026-08-03T18:00",
                "is_recurring": "on",
                "frequency": "weekly",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)

    def test_recurring_exceeding_cap_returns_error_without_creating(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-crear"),
            {
                "title": "Patrullaje",
                "start_at": "2026-08-03T18:00",
                "is_recurring": "on",
                "frequency": "weekly",
                "end_date": "2030-01-01",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)
        self.assertIn("end_date", response.json()["errors"])


class RecurrenceGenerationTests(TestCase):
    def test_weekly_with_count(self):
        start = datetime(2026, 8, 3, 18, 0, tzinfo=UTC)
        occurrences = generate_occurrence_starts(
            start, "weekly", occurrence_count=3
        )
        self.assertEqual(
            [o.date().isoformat() for o in occurrences],
            ["2026-08-03", "2026-08-10", "2026-08-17"],
        )

    def test_monthly_with_end_date_clamps_day_of_month(self):
        start = datetime(2026, 1, 31, 9, 0, tzinfo=UTC)
        occurrences = generate_occurrence_starts(
            start, "monthly", end_date=date(2026, 4, 1)
        )
        self.assertEqual(
            [o.date().isoformat() for o in occurrences],
            ["2026-01-31", "2026-02-28", "2026-03-31"],
        )

    def test_raises_when_exceeding_cap(self):
        start = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        with self.assertRaises(TooManyOccurrences):
            generate_occurrence_starts(
                start, "weekly", end_date=date(2030, 1, 1)
            )

    def test_occurrence_count_at_exactly_the_cap_is_allowed(self):
        start = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        occurrences = generate_occurrence_starts(
            start, "weekly", occurrence_count=MAX_OCCURRENCES
        )
        self.assertEqual(len(occurrences), MAX_OCCURRENCES)


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


class EventDeleteSeriesViewTests(TestCase):
    def setUp(self):
        self.group = uuid.uuid4()
        self.past = Event.objects.create(
            title="Patrullaje (pasado)",
            start_at=datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
            recurring_group=self.group,
        )
        self.current = Event.objects.create(
            title="Patrullaje (actual)",
            start_at=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
            recurring_group=self.group,
        )
        self.future = Event.objects.create(
            title="Patrullaje (futuro)",
            start_at=datetime(2026, 9, 1, 18, 0, tzinfo=UTC),
            recurring_group=self.group,
        )

    def delete_series_url(self, event=None):
        return reverse(
            "calendario-eventos-eliminar-serie",
            args=[(event or self.current).pk],
        )

    def test_requires_authentication(self):
        response = self.client.delete(self.delete_series_url())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Event.objects.count(), 3)

    def test_requires_staff(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.delete(self.delete_series_url())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Event.objects.count(), 3)

    def test_deletes_current_and_future_but_not_past(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.delete(self.delete_series_url())

        self.assertEqual(response.status_code, 204)
        self.assertTrue(Event.objects.filter(pk=self.past.pk).exists())
        self.assertFalse(Event.objects.filter(pk=self.current.pk).exists())
        self.assertFalse(Event.objects.filter(pk=self.future.pk).exists())

    def test_does_not_affect_events_in_other_groups(self):
        other_group_event = Event.objects.create(
            title="Otra serie",
            start_at=datetime(2026, 9, 15, 18, 0, tzinfo=UTC),
            recurring_group=uuid.uuid4(),
        )
        unrelated_event = Event.objects.create(
            title="Evento suelto",
            start_at=datetime(2026, 9, 20, 18, 0, tzinfo=UTC),
        )
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        self.client.delete(self.delete_series_url())

        self.assertTrue(Event.objects.filter(pk=other_group_event.pk).exists())
        self.assertTrue(Event.objects.filter(pk=unrelated_event.pk).exists())

    def test_deleting_series_cascades_confirmations(self):
        resident = create_user("residente")
        Confirmation.objects.create(user=resident, event=self.future)
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        self.client.delete(self.delete_series_url())

        self.assertEqual(Confirmation.objects.count(), 0)

    def test_non_recurring_event_falls_back_to_single_delete(self):
        standalone = Event.objects.create(
            title="Evento único",
            start_at=datetime(2026, 8, 15, 18, 0, tzinfo=UTC),
        )
        # Also recurring_group=None, and starts after `standalone`.
        # A naive `filter(recurring_group=event.recurring_group,
        # start_at__gte=event.start_at)` (without the `is None` special
        # case) would match both of these and delete them together.
        later_standalone = Event.objects.create(
            title="Otro evento único",
            start_at=datetime(2026, 8, 20, 18, 0, tzinfo=UTC),
        )
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.delete(self.delete_series_url(standalone))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Event.objects.filter(pk=standalone.pk).exists())
        self.assertTrue(Event.objects.filter(pk=later_standalone.pk).exists())
        self.assertEqual(Event.objects.count(), 4)

    def test_deleting_nonexistent_event_returns_404(self):
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.delete(
            reverse(
                "calendario-eventos-eliminar-serie",
                args=[self.future.pk + 999],
            )
        )

        self.assertEqual(response.status_code, 404)


class EventConfirmViewTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Café con vecinos",
            start_at=datetime(2026, 8, 20, 18, 0, tzinfo=UTC),
        )

    def confirm_url(self):
        return reverse("calendario-eventos-confirmar", args=[self.event.pk])

    def test_requires_authentication(self):
        response = self.client.post(self.confirm_url())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Confirmation.objects.count(), 0)

    def test_resident_can_confirm(self):
        resident = create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.post(self.confirm_url())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["extendedProps"]["confirmed"])
        self.assertTrue(
            Confirmation.objects.filter(
                user=resident, event=self.event
            ).exists()
        )

    def test_staff_can_also_confirm(self):
        # Confirming attendance isn't a staff-only action - any
        # authenticated resident, staff or not, can do it.
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")

        response = self.client.post(self.confirm_url())

        self.assertEqual(response.status_code, 200)

    def test_confirming_twice_is_idempotent(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        self.client.post(self.confirm_url())
        response = self.client.post(self.confirm_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Confirmation.objects.count(), 1)

    def test_resident_can_cancel_confirmation(self):
        resident = create_user("residente")
        Confirmation.objects.create(user=resident, event=self.event)
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.delete(self.confirm_url())

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Confirmation.objects.exists())

    def test_cancelling_when_not_confirmed_is_a_noop(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.delete(self.confirm_url())

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Confirmation.objects.count(), 0)

    def test_one_users_confirmation_does_not_affect_another(self):
        resident_a = create_user("residente_a")
        resident_b = create_user("residente_b")
        Confirmation.objects.create(user=resident_a, event=self.event)

        self.client.login(
            username=resident_b.username, password="clave-segura-123"
        )
        self.client.delete(self.confirm_url())

        self.assertTrue(
            Confirmation.objects.filter(
                user=resident_a, event=self.event
            ).exists()
        )

    def test_confirmed_count_includes_other_users_existing_confirmations(
        self,
    ):
        other_resident = create_user("otro_residente")
        Confirmation.objects.create(user=other_resident, event=self.event)
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.post(self.confirm_url())

        self.assertEqual(response.json()["extendedProps"]["confirmedCount"], 2)

    def test_confirming_nonexistent_event_returns_404(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.post(
            reverse("calendario-eventos-confirmar", args=[self.event.pk + 999])
        )

        self.assertEqual(response.status_code, 404)


class BuildEventIcsTests(TestCase):
    def test_includes_core_fields(self):
        event = Event.objects.create(
            title="Café con vecinos",
            description="Traer sillas",
            location="Casa comunal",
            start_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
            end_at=datetime(2026, 9, 20, 16, 0, tzinfo=UTC),
        )

        ics = build_event_ics(event)

        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn(f"UID:event-{event.pk}@arbolesdelaantigua.org", ics)
        self.assertIn("DTSTART:20260920T150000Z", ics)
        self.assertIn("DTEND:20260920T160000Z", ics)
        self.assertIn("SUMMARY:Café con vecinos", ics)
        self.assertIn("DESCRIPTION:Traer sillas", ics)
        self.assertIn("LOCATION:Casa comunal", ics)

    def test_missing_end_at_defaults_to_one_hour_duration(self):
        event = Event.objects.create(
            title="Café con vecinos",
            start_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        )

        ics = build_event_ics(event)

        self.assertIn("DTSTART:20260920T150000Z", ics)
        self.assertIn("DTEND:20260920T160000Z", ics)

    def test_meeting_link_is_appended_to_location(self):
        event = Event.objects.create(
            title="Reunión virtual",
            location="Casa comunal",
            meeting_link="https://us02web.zoom.us/j/123456789",
            start_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        )

        ics = build_event_ics(event)

        self.assertIn(
            "LOCATION:Casa comunal (https://us02web.zoom.us/j/123456789)",
            ics,
        )

    def test_meeting_link_alone_is_used_as_location_when_no_location_set(
        self,
    ):
        event = Event.objects.create(
            title="Reunión virtual",
            meeting_link="https://us02web.zoom.us/j/123456789",
            start_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        )

        ics = build_event_ics(event)

        self.assertIn(
            "LOCATION:https://us02web.zoom.us/j/123456789",
            ics,
        )

    def test_escapes_special_characters_in_text_fields(self):
        event = Event.objects.create(
            title="Reunión; anual, café\\pan",
            start_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        )

        ics = build_event_ics(event)

        self.assertIn("SUMMARY:Reunión\\; anual\\, café\\\\pan", ics)


@override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
class EventIcsViewTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Café con vecinos",
            start_at=datetime(2026, 8, 20, 18, 0, tzinfo=UTC),
        )

    def ics_url(self):
        return reverse("calendario-eventos-ics", args=[self.event.pk])

    def test_requires_authentication(self):
        response = self.client.get(self.ics_url())
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={self.ics_url()}",
        )

    def test_resident_can_download(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.get(self.ics_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"], "text/calendar; charset=utf-8"
        )
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(b"SUMMARY:Caf\xc3\xa9 con vecinos", response.content)

    def test_downloading_nonexistent_event_returns_404(self):
        create_user("residente")
        self.client.login(username="residente", password="clave-segura-123")

        response = self.client.get(
            reverse("calendario-eventos-ics", args=[self.event.pk + 999])
        )

        self.assertEqual(response.status_code, 404)

    def test_exported_time_matches_the_local_time_a_staff_member_typed(
        self,
    ):
        # End-to-end regression test for the originally reported bug: a
        # staff member creates an event meaning 15:00 Costa Rica local
        # time, and the downloaded .ics must encode the true UTC
        # equivalent (21:00Z), not the raw "15:00Z" Google Calendar/
        # Outlook would otherwise mis-display 6 hours early.
        create_user("admin", is_staff=True)
        self.client.login(username="admin", password="clave-segura-123")
        self.client.post(
            reverse("calendario-eventos-crear"),
            {"title": "Café virtual", "start_at": "2026-09-25T15:00"},
        )
        event = Event.objects.get(title="Café virtual")

        response = self.client.get(
            reverse("calendario-eventos-ics", args=[event.pk])
        )

        self.assertIn(b"DTSTART:20260925T210000Z", response.content)
