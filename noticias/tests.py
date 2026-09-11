from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from .content import get_article, list_articles

# The default STORAGES config uses a manifest-based static files storage
# (see config/settings.py) that requires `collectstatic` to have run. Tests
# that render full pages need the plain storage instead.
_STORAGES_WITHOUT_MANIFEST = {
    **settings.STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def write_article(directory, filename, content):
    (directory / filename).write_text(content, encoding="utf-8")


class ContentParsingTests(TestCase):
    def test_parses_front_matter_and_renders_markdown_body(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-15-primer-articulo.md",
                "---\n"
                'title: "Primer artículo"\n'
                'summary: "Resumen corto"\n'
                "image: images/noticias/primer-articulo/portada.jpg\n"
                "---\n\n"
                "Cuerpo en **negrita**.\n",
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.slug, "primer-articulo")
        self.assertEqual(article.date.isoformat(), "2026-01-15")
        self.assertEqual(article.title, "Primer artículo")
        self.assertEqual(article.summary, "Resumen corto")
        self.assertEqual(
            article.image, "images/noticias/primer-articulo/portada.jpg"
        )
        self.assertIn("<strong>negrita</strong>", article.html)

    @override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
    def test_resolves_inline_body_image_src_through_static(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-15-con-imagen.md",
                '---\ntitle: "Con imagen"\n---\n\n'
                "![Foto](images/noticias/con-imagen/foto.jpg)\n",
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertIn(
            'src="/static/images/noticias/con-imagen/foto.jpg"',
            articles[0].html,
        )

    def test_leaves_absolute_image_urls_untouched(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-15-imagen-externa.md",
                '---\ntitle: "Imagen externa"\n---\n\n'
                "![Foto](https://example.com/foto.jpg)\n",
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertIn('src="https://example.com/foto.jpg"', articles[0].html)

    def test_skips_file_without_a_title(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-15-sin-titulo.md",
                "cuerpo sin encabezado de metadatos",
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertEqual(articles, [])

    def test_skips_file_with_invalid_front_matter_yaml(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-15-mal-formado.md",
                '---\ntitle: "Falta cerrar comillas\n---\n\nCuerpo.\n',
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertEqual(articles, [])

    def test_skips_draft_articles(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-15-borrador.md",
                '---\ntitle: "Todavía no"\ndraft: true\n---\n\nCuerpo.\n',
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()
                article = get_article("borrador")

        self.assertEqual(articles, [])
        self.assertIsNone(article)

    def test_ignores_files_not_matching_the_date_slug_filename_pattern(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path, "notas.md", '---\ntitle: "Notas"\n---\n\nCuerpo.\n'
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertEqual(articles, [])

    def test_articles_are_sorted_by_date_descending(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_article(
                tmp_path,
                "2026-01-01-mas-antiguo.md",
                '---\ntitle: "Más antiguo"\n---\n\nCuerpo.\n',
            )
            write_article(
                tmp_path,
                "2026-06-01-mas-reciente.md",
                '---\ntitle: "Más reciente"\n---\n\nCuerpo.\n',
            )
            with patch("noticias.content.CONTENT_DIR", tmp_path):
                articles = list_articles()

        self.assertEqual(
            [article.slug for article in articles],
            ["mas-reciente", "mas-antiguo"],
        )

    def test_get_article_returns_none_for_unknown_slug(self):
        with (
            TemporaryDirectory() as tmp,
            patch("noticias.content.CONTENT_DIR", Path(tmp)),
        ):
            self.assertIsNone(get_article("no-existe"))


@override_settings(STORAGES=_STORAGES_WITHOUT_MANIFEST)
class NoticiasViewTests(TestCase):
    def setUp(self):
        tmp_dir = TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.content_dir = Path(tmp_dir.name)
        patcher = patch("noticias.content.CONTENT_DIR", self.content_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        write_article(
            self.content_dir,
            "2026-01-15-primer-articulo.md",
            '---\ntitle: "Primer artículo"\n---\n\nCuerpo.\n',
        )

    def test_list_view_is_public_and_shows_articles(self):
        response = self.client.get(reverse("noticias"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Primer artículo")

    def test_detail_view_returns_the_matching_article(self):
        response = self.client.get(
            reverse("noticias-detalle", args=["primer-articulo"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Primer artículo")

    def test_detail_view_404s_for_unknown_slug(self):
        response = self.client.get(
            reverse("noticias-detalle", args=["no-existe"])
        )
        self.assertEqual(response.status_code, 404)
