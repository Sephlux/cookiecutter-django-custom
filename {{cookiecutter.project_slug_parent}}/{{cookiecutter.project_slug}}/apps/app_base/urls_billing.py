from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.plans_view, name="plans"),
    # HTMX fragments (keep OUT of /plans/** so redirects don't break the toggle)
    path("fragments/plans-section/", views.plans_section_fragment, name="plans_section_fragment"),

    path("subscribe/", views.create_checkout_session, name="subscribe"),
    path("portal/", views.create_portal_session, name="portal"),
    path("status-fragment/", views.subscription_status_fragment, name="status_fragment"),

    # Redirect anything under /billing/plans/** back to /billing/ (no kwargs forwarding)
    path("plans/<path:unused_path>", RedirectView.as_view(url="../", permanent=False)),
    path("plans/", RedirectView.as_view(url="/billing/", permanent=False)),

]
