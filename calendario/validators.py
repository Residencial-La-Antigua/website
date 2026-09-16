from urllib.parse import urlparse

from django.core.exceptions import ValidationError

ALLOWED_MEETING_LINK_DOMAINS = (
    "zoom.us",
    "meet.google.com",
    "teams.microsoft.com",
    "discord.com",
    "discord.gg",
    "slack.com",
)


def validate_meeting_link_domain(value):
    hostname = (urlparse(value).hostname or "").lower()
    is_allowed = any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in ALLOWED_MEETING_LINK_DOMAINS
    )
    if not is_allowed:
        raise ValidationError(
            "El enlace debe pertenecer a Zoom, Google Meet, Microsoft Teams, "
            "Discord o Slack."
        )
