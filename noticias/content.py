import re
from dataclasses import dataclass
from datetime import date

import frontmatter
import markdown
import yaml
from django.conf import settings
from django.templatetags.static import static

CONTENT_DIR = settings.BASE_DIR / "content" / "noticias"

_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9-]+)\.md$")
_IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")')


def _resolve_image_srcs(html):
    # Article bodies reference images the same way the `image` front matter
    # field does: a path relative to the static root (e.g.
    # "images/noticias/<slug>/foto.jpg"), not a literal URL. Resolving it
    # through Django's static() here - rather than leaving it for the
    # template - keeps this in sync with STATIC_URL/storage the same way
    # {% static %} would.
    def replace(match):
        prefix, src, suffix = match.groups()
        if src.startswith(("http://", "https://", "/")):
            return match.group(0)
        return f"{prefix}{static(src)}{suffix}"

    return _IMG_SRC_RE.sub(replace, html)


@dataclass
class Article:
    slug: str
    date: date
    title: str
    summary: str
    image: str | None
    html: str


def _parse_file(path):
    match = _FILENAME_RE.match(path.name)
    if not match:
        return None

    # Article files are edited by non-technical team members via GitHub's
    # web UI, outside of any code review that would catch a typo in the
    # front matter. A single malformed file should disappear from the
    # public list rather than break the page for everyone, so any parsing
    # failure here is treated the same as "not an article".
    try:
        post = frontmatter.load(path)
    except (OSError, yaml.YAMLError):
        return None

    title = post.get("title")
    if not title or post.get("draft"):
        return None

    image = post.get("image")

    return Article(
        slug=match.group("slug"),
        date=date.fromisoformat(match.group(1)),
        title=str(title),
        summary=str(post.get("summary", "")),
        image=str(image) if image is not None else None,
        html=_resolve_image_srcs(
            markdown.markdown(post.content, extensions=["extra", "sane_lists"])
        ),
    )


def list_articles():
    if not CONTENT_DIR.is_dir():
        return []
    articles = (
        article
        for path in CONTENT_DIR.glob("*.md")
        if (article := _parse_file(path)) is not None
    )
    return sorted(articles, key=lambda article: article.date, reverse=True)


def get_article(slug):
    for article in list_articles():
        if article.slug == slug:
            return article
    return None
