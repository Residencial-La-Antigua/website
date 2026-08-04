from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(
        self, username, email=None, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_active", True)
        return super().create_superuser(
            username, email, password, **extra_fields
        )


class User(AbstractUser):
    """Neighbor account. Inactive by default until an admin approves it."""

    is_active = models.BooleanField(
        default=False,
        help_text="Unapproved neighbor accounts stay inactive and cannot log in.",
    )

    objects = UserManager()
