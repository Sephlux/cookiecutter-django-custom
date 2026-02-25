from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
{%- if cookiecutter.use_async == 'y' %}
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
{%- endif %}
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView
{%- if cookiecutter.use_drf == 'y' %}
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
{%- endif %}
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from {{cookiecutter.project_slug}}.apps.app_base import views as app_base_views


def root_view(request):
    if request.user.is_authenticated:
        return redirect("/app/")
    return redirect(reverse("account_login"))


def catch_all_org_to_dashboard(request, org_slug: str, unused_path: str | None = None):
    return redirect(f"/o/{org_slug}/")


def catch_all_to_login(request, unused_path: str | None = None):
    login_url = reverse("account_login")
    next_param = request.get_full_path()
    return redirect(f"{login_url}")

urlpatterns = [
    # Django Admin, use { url 'admin:index' }
    path(settings.ADMIN_URL, admin.site.urls),

    # Root: authenticated -> /app/ ; anonymous -> login
    path("", root_view, name="root"),

    # User management
    path("accounts/", include("allauth.urls")),
    # Stripe (global, not org-scoped)
    path("stripe/webhook/", app_base_views.stripe_webhook, name="stripe-webhook"),


    # Post-login redirect to last-used org
    path("app/", app_base_views.org_redirect_view, name="org-redirect"),
    # Org switch (keeps current page when possible)
    path("o/switch/<slug:org_slug>/", app_base_views.org_switch_view, name="org-switch"),
    # Org-scoped app
    path("o/<slug:org_slug>/", include("{{cookiecutter.project_slug}}.apps.app_base.urls")),

    # Your stuff: custom urls includes go here
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
{%- if cookiecutter.use_async == 'y' %}
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()
{%- endif %}
{% if cookiecutter.use_drf == 'y' %}
# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router")),
    # DRF auth token
    path("api/auth-token/", obtain_auth_token, name="obtain_auth_token"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]
{%- endif %}

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]

    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
urlpatterns += [
    path("o/<slug:org_slug>/<path:unused_path>", catch_all_org_to_dashboard),
    path("<path:unused_path>", catch_all_to_login),
]
