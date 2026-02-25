from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User, UserOrganizationState
from organizations.models import OrganizationUser, OrganizationOwner, Organization

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        {%- if cookiecutter.username_type == "email" %}
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        {%- else %}
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        {%- endif %}
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["{{cookiecutter.username_type}}", "name", "is_superuser"]
    search_fields = ["name"]
    {%- if cookiecutter.username_type == "email" %}
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    {%- endif %}

@admin.register(UserOrganizationState)
class UserOrganizationStateAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        # show all concrete model fields as columns
        return [f.name for f in self.model._meta.concrete_fields]

    search_fields = ("user__email", "personal_org__name", "last_used_org__name")


try:
    admin.site.unregister(OrganizationUser)
    admin.site.unregister(OrganizationOwner)
    admin.site.unregister(Organization)
except admin.sites.NotRegistered:
    pass

@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        # show all concrete model fields as columns
        return [f.name for f in self.model._meta.concrete_fields]

@admin.register(OrganizationOwner)
class OrganizationUserAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        # show all concrete model fields as columns
        return [f.name for f in self.model._meta.concrete_fields]

@admin.register(Organization)
class OrganizationUserAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        # show all concrete model fields as columns
        return [f.name for f in self.model._meta.concrete_fields]



