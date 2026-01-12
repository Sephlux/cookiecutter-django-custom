import json
from datetime import datetime

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt

from .models import BillingCustomer

stripe.api_key = settings.STRIPE_SECRET_KEY


def _get_or_create_billing_customer(user):
    bc, _ = BillingCustomer.objects.get_or_create(user=user)
    if not bc.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email or None, metadata={"django_user_id": user.pk})
        bc.stripe_customer_id = customer.id
        bc.save(update_fields=["stripe_customer_id"])
    return bc


@login_required
def plans_view(request):
    price_ids = getattr(settings, "STRIPE_PRICE_IDS", "")
    if isinstance(price_ids, str):
        price_ids = [p.strip() for p in price_ids.split(",") if p.strip()]

    prices = []
    for pid in price_ids:
        try:
            pr = stripe.Price.retrieve(pid, expand=["product"])
            prices.append(pr)
        except Exception:
            # skip invalid price ids
            continue

    plan_labels = getattr(settings, "PLAN_LABELS", {})
    plan_descriptions = getattr(settings, "PLAN_DESCRIPTIONS", {})
    return render(
        request,
        "billing/plans.html",
        {
            "prices": prices,
            "plan_labels": plan_labels,
            "plan_descriptions": plan_descriptions,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@login_required
def subscription_status_fragment(request):
    bc = BillingCustomer.objects.filter(user=request.user).first()
    return render(request, "billing/_subscription_status.html", {"bc": bc})


@login_required
def create_checkout_session(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    price_id = request.POST.get("price_id")
    if not price_id:
        return HttpResponseBadRequest("Missing price_id")

    bc = _get_or_create_billing_customer(request.user)
    success_url = request.build_absolute_uri(reverse("billing:plans")) + "?checkout=success"
    cancel_url = request.build_absolute_uri(reverse("billing:plans")) + "?checkout=cancel"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=bc.stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            billing_address_collection="auto",
            customer_update={"address": "auto"},
            subscription_data={"metadata": {"django_user_id": request.user.pk}},
            ui_mode="hosted",
        )
    except Exception as e:
        return HttpResponseBadRequest(str(e))

    resp = HttpResponse(status=204)
    resp["HX-Redirect"] = session.url
    return resp


@login_required
def create_portal_session(request):
    bc = _get_or_create_billing_customer(request.user)
    return_url = request.build_absolute_uri(reverse("billing:plans"))
    try:
        portal = stripe.billing_portal.Session.create(
            customer=bc.stripe_customer_id,
            return_url=return_url,
        )
    except Exception as e:
        return HttpResponseBadRequest(str(e))

    resp = HttpResponse(status=204)
    resp["HX-Redirect"] = portal.url
    return resp


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = json.loads(payload.decode("utf-8"))
    except Exception:
        return HttpResponseForbidden("Invalid signature")

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        _sync_subscription_by_customer(customer_id, subscription_id)

    elif event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        subscription = data
        customer_id = subscription.get("customer")
        subscription_id = subscription.get("id")
        _sync_subscription_by_customer(customer_id, subscription_id)

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")
        if subscription_id:
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                _sync_subscription_by_customer(sub.get("customer"), sub.get("id"))
            except Exception:
                pass

    return HttpResponse(status=200)


def _sync_subscription_by_customer(customer_id: str | None, subscription_id: str | None):
    if not customer_id:
        return
    try:
        bc = BillingCustomer.objects.get(stripe_customer_id=customer_id)
    except BillingCustomer.DoesNotExist:
        return

    if not subscription_id:
        bc.subscription_status = None
        bc.price_id = None
        bc.current_period_end = None
        bc.save(update_fields=["subscription_status", "price_id", "current_period_end"])
        return

    try:
        subscription = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])
    except Exception:
        return

    status = subscription.get("status")
    items = subscription.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None
    period_end = subscription.get("current_period_end")
    bc.subscription_status = status
    bc.price_id = price_id
    bc.current_period_end = make_aware(datetime.fromtimestamp(period_end)) if period_end else None
    bc.save(update_fields=["subscription_status", "price_id", "current_period_end"])
