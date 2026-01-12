from django.contrib import admin
from .models import BillingCustomer

@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = ("user", "stripe_customer_id", "subscription_status", "price_id", "current_period_end")
    search_fields = ("user__email", "stripe_customer_id", "price_id")
