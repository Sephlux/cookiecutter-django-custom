
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import ForeignKey
from django.db.models import OneToOneField
from django.db.models import PROTECT
from django.db.models import SET_NULL

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for Cookiecutter Test.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

class UserOrganizationState(models.Model):
    """
    Tracks:
      - the user's explicit personal org (slug p-...)
      - the last used org (for default selection after login)
    """
    user = OneToOneField("users.User", on_delete=models.CASCADE, related_name="org_state")

    personal_org = ForeignKey(
        "organizations.Organization",
        on_delete=PROTECT,
        related_name="personal_for_users",
        null=True,
        blank=True,
    )

    last_used_org = ForeignKey(
        "organizations.Organization",
        on_delete=SET_NULL,
        related_name="last_used_by_users",
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"UserOrganizationState(user_id={self.user_id})"
