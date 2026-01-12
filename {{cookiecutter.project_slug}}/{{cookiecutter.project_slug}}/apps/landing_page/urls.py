from django.contrib.auth.decorators import login_not_required
from django.conf import settings
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.shortcuts import render, redirect


@login_not_required
def landing_page(request):
    return render(request, "landing_page/index.html")

# Catch-all that redirects to "/" and does NOT require login
@login_not_required
def catch_all_to_root(request, unused_path=None):
    return redirect("/")


urlpatterns = [
    path("", landing_page, name="landing-page"),
]

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
    path("<path:unused_path>", catch_all_to_root),
]
