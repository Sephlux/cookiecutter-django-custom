from django.conf import settings
from django.db import models

class BillingCustomer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_customer")
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    subscription_status = models.CharField(max_length=64, blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    price_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.user} - {self.subscription_status or 'no-subscription'}"
