from __future__ import annotations

import re
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from organizations.models import Organization, OrganizationUser

from src.apps.users.models import UserOrganizationState


@dataclass(frozen=True)
class OrgResolution:
    organization: Organization
    membership: OrganizationUser


_ORG_PATH_RE = re.compile(r"^/o/(?P<org_slug>[-a-zA-Z0-9_]+)/")


class OrganizationFromUrlMiddleware:
    """
    New-style middleware.

    - Resolves org from URL path prefix: /o/<org_slug>/...
    - Sets request.organization
    - Enforces membership for authenticated users
    - Updates last_used_org
    - Ignores real Django admin URLs (e.g. /admin/...), but NOT /o/admin/ (valid org slug)
    """

    def __init__(self, get_response):
        self.get_response = get_response

        admin_prefix = "/" + str(getattr(settings, "ADMIN_URL", "admin/")).lstrip("/")
        if not admin_prefix.endswith("/"):
            admin_prefix += "/"
        self._admin_prefix = admin_prefix

    def __call__(self, request: HttpRequest):
        request.organization = None  # type: ignore[attr-defined]

        # Ignore Django admin only (e.g. /admin/...). Keep /o/<slug>/... working.
        if request.path_info.startswith(self._admin_prefix):
            return self.get_response(request)

        m = _ORG_PATH_RE.match(request.path_info)
        if not m:
            return self.get_response(request)

        org_slug = m.group("org_slug")

        if not request.user.is_authenticated:
            login_url = reverse("account_login")
            next_param = request.get_full_path()
            return redirect(f"{login_url}?{urlencode({'next': next_param})}")

        resolution = self._resolve_for_user(request, org_slug)
        request.organization = resolution.organization  # type: ignore[attr-defined]

        state, _ = UserOrganizationState.objects.get_or_create(user=request.user)
        if state.last_used_org_id != resolution.organization.id:
            state.last_used_org = resolution.organization
            state.save(update_fields=["last_used_org"])

        return self.get_response(request)

    def _resolve_for_user(self, request: HttpRequest, org_slug: str) -> OrgResolution:
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist as e:
            raise Http404("Organization not found") from e

        membership = OrganizationUser.objects.filter(user=request.user, organization=org).first()
        if not membership:
            raise PermissionDenied("You do not have access to this organization")

        return OrgResolution(organization=org, membership=membership)
