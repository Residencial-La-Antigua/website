import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import User

logger = logging.getLogger(__name__)


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

    subject = "Nueva cuenta pendiente de aprobación"
    body = (
        f"El usuario «{user.username}» ({user.first_name} {user.last_name}) "
        f"se registró y está pendiente de aprobación.\n\n"
        f"Las cuentas nuevas pueden ser aprobadas desde /admin/accounts/user/."
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
