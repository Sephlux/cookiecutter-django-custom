from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("", views.plans_view, name="plans"),
    path("subscribe/", views.create_checkout_session, name="subscribe"),
    path("portal/", views.create_portal_session, name="portal"),
    path("webhook/", views.stripe_webhook, name="webhook"),
    path("status-fragment/", views.subscription_status_fragment, name="status_fragment"),
]
