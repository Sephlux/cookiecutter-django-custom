import json
import logging
from datetime import datetime

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from organizations.models import OrganizationUser

from .models import BillingCustomer
from ..users.models import UserOrganizationState

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

@login_required
def org_redirect_view(request):
    """
    Redirect to the user's last-used org (or personal org fallback).
    """
    state = UserOrganizationState.objects.filter(user=request.user).select_related("last_used_org", "personal_org").first()

    # 1) last used, if still a member
    if state and state.last_used_org_id:
        if OrganizationUser.objects.filter(user=request.user, organization=state.last_used_org).exists():
            return redirect(f"/o/{state.last_used_org.slug}/")

    # 2) any org membership (e.g. if state isn't created yet)
    membership = (
        OrganizationUser.objects.filter(user=request.user)
        .select_related("organization")
        .order_by("-id")
        .first()
    )
    if membership:
        if state:
            state.last_used_org = membership.organization
            state.save(update_fields=["last_used_org"])
        return redirect(f"/o/{membership.organization.slug}/")

    # 3) personal org must exist, but if it doesn't (edge case), go home
    if state and state.personal_org_id:
        return redirect(f"/o/{state.personal_org.slug}/")

    return redirect("/")


@login_required
def org_switch_view(request, org_slug: str):
    """
    Switch org while attempting to keep the current page by rewriting /o/<old>/... -> /o/<new>/...
    Accepts ?next=/o/<old>/some/path/
    """
    if not OrganizationUser.objects.filter(user=request.user, organization__slug=org_slug).exists():
        return HttpResponseForbidden("You do not have access to this organization")

    next_url = request.GET.get("next") or ""
    prefix = "/o/"
    if next_url.startswith(prefix):
        # Replace the first org segment
        parts = next_url.split("/", 4)  # ["", "o", "<old>", ...]
        if len(parts) >= 3 and parts[1] == "o":
            rewritten = f"/o/{org_slug}/"
            if len(parts) >= 4:
                rewritten += parts[3]
                if len(parts) == 5:
                    rewritten += f"/{parts[4]}"
            return redirect(rewritten)

    return redirect(f"/o/{org_slug}/")


def _get_or_create_billing_customer(user):
    bc, _ = BillingCustomer.objects.get_or_create(user=user)
    if not bc.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email or None, metadata={"django_user_id": user.pk})
        bc.stripe_customer_id = customer.id
        bc.save(update_fields=["stripe_customer_id"])
    return bc


def _stripe_catalog_cache_key(product_ids: list[str]) -> str:
    ids_key = "all" if not product_ids else ",".join(sorted(product_ids))
    return f"stripe:products_with_prices:{ids_key}"


def _purge_stripe_catalog_cache():
    try:
        cache.delete_pattern("stripe:products_with_prices:*")
    except Exception:
        logger.info("Cache backend does not support delete_pattern; relying on TTL.")


def _load_products_with_prices():
    cache_ttl = getattr(settings, "STRIPE_CACHE_TTL", 300)

    product_ids_setting = getattr(settings, "STRIPE_PRODUCT_IDS", "")
    if isinstance(product_ids_setting, str):
        product_ids = [p.strip() for p in product_ids_setting.split(",") if p.strip()]
    else:
        product_ids = product_ids_setting or []

    cache_key = _stripe_catalog_cache_key(product_ids)

    def _build():
        products = []
        try:
            if product_ids:
                stripe_products = []
                for pid in product_ids:
                    try:
                        stripe_products.append(stripe.Product.retrieve(pid))
                    except Exception:
                        logger.exception("Invalid product id: %s", pid)
                        continue
            else:
                stripe_products = list(stripe.Product.list(active=True, limit=100).auto_paging_iter())
        except Exception:
            logger.exception("Failed to load products from Stripe")
            stripe_products = []

        for prod in stripe_products:
            try:
                prod_prices = list(
                    stripe.Price.list(product=prod["id"], active=True, limit=100).auto_paging_iter()
                )
            except Exception:
                logger.exception("Failed to load prices for product %s", prod.get("id"))
                prod_prices = []

            monthly_price = next(
                (p for p in prod_prices if
                 p.get("type") == "recurring" and p.get("recurring", {}).get("interval") == "month"),
                None,
            )
            yearly_price = next(
                (p for p in prod_prices if
                 p.get("type") == "recurring" and p.get("recurring", {}).get("interval") == "year"),
                None,
            )
            products.append({"product": prod, "monthly_price": monthly_price, "yearly_price": yearly_price})

        return products

    return cache.get_or_set(cache_key, _build, cache_ttl)


@login_required
def plans_view(request, org_slug: str, *args, **kwargs):
    interval = request.GET.get("interval", "month")
    if interval not in ("month", "year"):
        interval = "month"

    products = _load_products_with_prices()
    plan_labels = getattr(settings, "PLAN_LABELS", {})
    plan_descriptions = getattr(settings, "PLAN_DESCRIPTIONS", {})
    plan_features = getattr(settings, "PLAN_FEATURES", {})  # optio_
    return render(
        request,
        "app_base/billing/plans.html",
        {
            "products": products,
            "plan_labels": plan_labels,
            "plan_descriptions": plan_descriptions,
            "plan_features": plan_features,
            "interval": interval,
            "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        },
    )


@login_required
def plans_section_fragment(request, org_slug: str, *args, **kwargs):
    interval = request.GET.get("interval", "month")
    if interval not in ("month", "year"):
        interval = "month"

    products = _load_products_with_prices()
    plan_labels = getattr(settings, "PLAN_LABELS", {})
    plan_descriptions = getattr(settings, "PLAN_DESCRIPTIONS", {})
    plan_features = getattr(settings, "PLAN_FEATURES", {})

    return render(
        request,
        "app_base/billing/_plans_section.html",
        {
            "products": products,
            "plan_labels": plan_labels,
            "plan_descriptions": plan_descriptions,
            "plan_features": plan_features,
            "interval": interval,
            "bc": getattr(request.user, "billing_customer", None),
        },
    )


@login_required
def subscription_status_fragment(request, org_slug: str, *args, **kwargs):
    bc = BillingCustomer.objects.filter(user=request.user).first()
    return render(request, "app_base/billing/_subscription_status.html", {"bc": bc})


@login_required
def create_checkout_session(request, org_slug: str, *args, **kwargs):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    price_id = request.POST.get("price_id")
    if not price_id:
        return HttpResponseBadRequest("Missing price_id")

    bc = _get_or_create_billing_customer(request.user)
    success_url = request.build_absolute_uri(reverse("billing:plans", kwargs={"org_slug": request.organization.slug})) + "?checkout=success"
    cancel_url = request.build_absolute_uri(reverse("billing:plans", kwargs={"org_slug": request.organization.slug})) + "?checkout=cancel"

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
def create_portal_session(request, org_slug: str, *args, **kwargs):
    bc = _get_or_create_billing_customer(request.user)
    return_url = request.build_absolute_uri(reverse("billing:plans", kwargs={"org_slug": request.organization.slug}))
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

    if event_type in (
            "product.created",
            "product.updated",
            "product.deleted",
            "price.created",
            "price.updated",
            "price.deleted",
    ):
        _purge_stripe_catalog_cache()

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        _sync_subscription_by_customer(customer_id, subscription_id)

    elif event_type in ("customer.subscription.created", "customer.subscription.updated",
                        "customer.subscription.deleted"):
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
