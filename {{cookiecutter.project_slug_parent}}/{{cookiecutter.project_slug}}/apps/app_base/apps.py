from django.apps import AppConfig

class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{{cookiecutter.project_slug}}.apps.app_base"
    verbose_name = "BaseApp"
