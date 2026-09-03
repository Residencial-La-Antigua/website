import hashlib

from django import template
from django.conf import settings

register = template.Library()

@register.filter
def analytics_id(user):
    """A stable, non-reversible per-resident ID for Umami's identify(),
    decoupled from the sequential integer user.pk."""
    if not user.is_authenticated:
        return ""
    raw = f"{settings.ANALYTICS_SALT}:{user.pk}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
