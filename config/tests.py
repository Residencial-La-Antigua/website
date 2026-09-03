from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

_STORAGES_WITHOUT_MANIFEST = {
    **settings.STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
class MigrationPageTests(TestCase):
    def test_root_keeps_existing_home_template(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")

    def test_noticias_placeholder_has_named_route(self):
        response = self.client.get(reverse("noticias"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "noticias.html")
        self.assertContains(response, "Estamos preparando este espacio")

    def test_migrated_home_renders_without_public_route(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        content = render_to_string("homemig.html", request=request)

        self.assertIn("Cuidamos los", content)
        self.assertIn("images/migration/general/Hero.jpg", content)
        self.assertIn("mig-report-dialog", content)
        self.assertNotIn("translations.js", content)
        self.assertNotIn("lang-dropdown", content)

    def test_anonymous_nav_has_primary_and_account_links(self):
        response = self.client.get(reverse("noticias"))
        content = response.content.decode()
        nav_start = content.index('<nav class="mig-primary-nav"')
        nav_end = content.index("</nav>", nav_start)
        primary_nav = content[nav_start:nav_end]

        expected_labels = (
            "Inicio",
            "Noticias",
            "Teléfonos Importantes",
            "Basura y Reciclaje",
            "Desechos no tradicionales",
            "Calendario",
        )
        positions = [primary_nav.index(label) for label in expected_labels]
        self.assertEqual(positions, sorted(positions))
        self.assertContains(response, "Iniciar sesión")
        self.assertContains(response, "Registrarse")
        self.assertContains(response, "Acompáñanos")

    def test_authenticated_nav_keeps_account_controls(self):
        user = User.objects.create_user(
            username="residente-migracion",
            password="clave-segura-123",
            street="Calle Principal",
            house_number="1",
            is_active=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("noticias"))

        self.assertContains(response, "Hola, residente-migracion")
        self.assertContains(response, "Mi cuenta")
        self.assertContains(response, "Cerrar sesión")
        self.assertNotContains(response, "Registrarse")