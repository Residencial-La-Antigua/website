import hashlib
from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings
from django.urls import reverse

from calendario.models import Confirmation, Event

from .templatetags.analytics import analytics_id

User = get_user_model()

# The default STORAGES config uses a manifest-based static files storage
# (see config/settings.py) that requires `collectstatic` to have run.
# Django's admin templates render {% static %} tags, so any test that
# renders an admin page needs the plain storage instead.
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


def create_superuser(username):
    return User.objects.create_superuser(
        username=username,
        email=f"{username}@example.com",
        password="clave-segura-123",
        street="Calle Principal",
        house_number="1",
    )


class AnalyticsIdFilterTests(TestCase):
    def test_anonymous_user_gets_empty_string(self):
        self.assertEqual(analytics_id(AnonymousUser()), "")

    def test_authenticated_user_gets_a_stable_hash(self):
        user = create_user("residente")
        self.assertEqual(analytics_id(user), analytics_id(user))
        self.assertNotEqual(analytics_id(user), "")

    def test_different_users_get_different_hashes(self):
        user_a = create_user("residente_a")
        user_b = create_user("residente_b")
        self.assertNotEqual(analytics_id(user_a), analytics_id(user_b))

    def test_hash_uses_the_salt_and_sha256_truncated_to_16_chars(self):
        user = create_user("residente")
        expected = hashlib.sha256(
            f"{settings.ANALYTICS_SALT}:{user.pk}".encode()
        ).hexdigest()[:16]
        self.assertEqual(analytics_id(user), expected)

    def test_reads_the_salt_from_settings_not_a_hardcoded_value(self):
        user = create_user("residente")
        before = analytics_id(user)
        with override_settings(ANALYTICS_SALT="una-sal-completamente-distinta"):
            after = analytics_id(user)
        self.assertNotEqual(before, after)


@override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
class ConfirmationInlineTests(TestCase):
    """HU-10: an admin can see a resident's full confirmation history on
    the resident's own admin page."""

    def setUp(self):
        self.admin = create_superuser("admin")
        self.client.login(username="admin", password="clave-segura-123")
        self.resident = create_user("residente")

    def change_url(self):
        return reverse("admin:accounts_user_change", args=[self.resident.pk])

    def test_shows_the_users_confirmation_history(self):
        event = Event.objects.create(
            title="Jornada de siembra",
            start_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        )
        Confirmation.objects.create(user=self.resident, event=event)

        response = self.client.get(self.change_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jornada de siembra")

    def test_confirmations_are_ordered_chronologically_by_event_date(self):
        later = Event.objects.create(
            title="Evento tardío",
            start_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        )
        earlier = Event.objects.create(
            title="Evento temprano",
            start_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
        )
        # Created out of chronological order on purpose, to prove the
        # display order comes from the event date, not creation order.
        Confirmation.objects.create(user=self.resident, event=later)
        Confirmation.objects.create(user=self.resident, event=earlier)

        response = self.client.get(self.change_url())

        content = response.content.decode()
        self.assertLess(
            content.index("Evento temprano"), content.index("Evento tardío")
        )

    def test_does_not_show_another_users_confirmations(self):
        other_resident = create_user("otro_residente")
        event = Event.objects.create(
            title="Evento de otra persona",
            start_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        )
        Confirmation.objects.create(user=other_resident, event=event)

        response = self.client.get(self.change_url())

        self.assertNotContains(response, "Evento de otra persona")

    def test_inline_has_no_add_capability(self):
        response = self.client.get(self.change_url())
        # The formset prefix is "confirmations" (from Confirmation.user's
        # related_name), not the default "confirmation_set", and the
        # rendered *id* attribute additionally gets Django's standard
        # "id_" prefix (id="id_confirmations-TOTAL_FORMS") - matching on
        # the plain "name" attribute instead avoids that trap. An inline
        # with no add permission renders 0 extra blank forms.
        self.assertContains(
            response, 'name="confirmations-TOTAL_FORMS" value="0"'
        )


@override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
class ConfirmationAdminDeleteTests(TestCase):
    """HU-11: an admin can remove a specific user's confirmation, and it
    disappears from both the event's and the user's records."""

    def setUp(self):
        self.admin = create_superuser("admin")
        self.client.login(username="admin", password="clave-segura-123")
        self.resident = create_user("residente")
        self.event = Event.objects.create(
            title="Jornada de siembra",
            start_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        )
        self.confirmation = Confirmation.objects.create(
            user=self.resident, event=self.event
        )

    def test_admin_can_delete_a_users_confirmation(self):
        delete_url = reverse(
            "admin:calendario_confirmation_delete",
            args=[self.confirmation.pk],
        )

        response = self.client.post(delete_url, {"post": "yes"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Confirmation.objects.filter(pk=self.confirmation.pk).exists()
        )

    def test_deleted_confirmation_disappears_from_users_history(self):
        delete_url = reverse(
            "admin:calendario_confirmation_delete",
            args=[self.confirmation.pk],
        )
        self.client.post(delete_url, {"post": "yes"})

        response = self.client.get(
            reverse("admin:accounts_user_change", args=[self.resident.pk])
        )

        # Not assertNotContains(response, "Jornada de siembra") - Django's
        # own delete-success flash message echoes the deleted object's
        # __str__ (which includes the event title) on this exact next
        # page load, so that text legitimately appears on the page
        # without the confirmation still being listed. Check the inline
        # formset's own row count instead, which is what's actually
        # being asserted here.
        self.assertContains(
            response, 'name="confirmations-INITIAL_FORMS" value="0"'
        )

    def test_non_staff_cannot_reach_admin(self):
        self.client.logout()
        create_user("residente_normal")
        self.client.login(
            username="residente_normal", password="clave-segura-123"
        )

        response = self.client.get(
            reverse(
                "admin:calendario_confirmation_delete",
                args=[self.confirmation.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Confirmation.objects.filter(pk=self.confirmation.pk).exists()
        )
