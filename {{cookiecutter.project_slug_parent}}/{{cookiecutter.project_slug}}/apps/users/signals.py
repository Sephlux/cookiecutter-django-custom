from __future__ import annotations

import re

from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.db import transaction

from organizations.models import Organization, OrganizationOwner, OrganizationUser

from .models import UserOrganizationState


def _derive_personal_org_name(email: str) -> str:
    local = (email or "").split("@", 1)[0].split("+", 1)[0]
    local = re.sub(r"[._-]+", " ", local).strip()
    return local.title() or "Personal Workspace"


@receiver(user_signed_up)
@transaction.atomic
def create_personal_org_on_signup(request, user, **kwargs):
    state, _ = UserOrganizationState.objects.get_or_create(user=user)
    if state.personal_org_id:
        return

    # Explicit personal slug; stable and collision-free
    personal_slug = f"p-{user.pk}"

    org = Organization.objects.create(
        name=_derive_personal_org_name(user.email or ""),
        slug=personal_slug,
    )

    org_user = OrganizationUser.objects.create(user=user, organization=org, is_admin=True)
    OrganizationOwner.objects.create(organization=org, organization_user=org_user)

    state.personal_org = org
    state.last_used_org = org
    state.save(update_fields=["personal_org", "last_used_org"])

