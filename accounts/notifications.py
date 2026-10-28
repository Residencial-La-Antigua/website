import logging
import re

from django.conf import settings
from django.core.mail import send_mail

from .models import User

logger = logging.getLogger(__name__)


def _collapse_whitespace(text):
    """Flatten any embedded newlines/tabs so untrusted text can't inject
    extra lines into an email body."""
    return re.sub(r"\s+", " ", text).strip()


def notify_staff_of_new_signup(user):
    """Email every active staff user that `user` needs approval.

    Never raises: a broken SMTP config must not break registration for the
    registrant. Failures are logged instead.
    """
    recipients = list(
        User.objects.filter(is_staff=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        return

    full_name = _collapse_whitespace(f"{user.first_name} {user.last_name}")
    username = _collapse_whitespace(user.username)

    subject = "La Antigua - Aprobar cuenta nueva"
    # The registrant's own name is untrusted, unreviewed free text, so it's
    # quoted and placed last; never ahead of, or blended into, the
    # instruction, so it can't be mistaken for a system-authored message.
    body = (
        "Una cuenta nueva está pendiente de aprobación.\n"
        "Apruébala desde /admin/accounts/user/.\n\n"
        f'Nombre proporcionado por el usuario: "{full_name}" '
        f'(usuario: "{username}")'
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "No se pudo enviar el correo de aviso para la nueva cuenta creada por %s (%s %s)",
            user.username,
            user.first_name,
            user.last_name,
        )
