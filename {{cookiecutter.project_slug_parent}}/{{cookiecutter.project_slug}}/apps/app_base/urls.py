from django.urls import path, include
from django.views.generic import TemplateView

from . import urls_billing

urlpatterns = [
    path("billing/", include((urls_billing.urlpatterns, urls_billing.app_name), namespace="billing")),
    path("", TemplateView.as_view(template_name="app_base/dashboard/dashboard.html"), name="home"),
    path("settings/", TemplateView.as_view(template_name="app_base/settings/settings.html"), name="settings"),
]
