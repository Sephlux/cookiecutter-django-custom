from decimal import Decimal, ROUND_HALF_UP

from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    try:
        return d.get(key)
    except Exception:
        return None


# Common "zero-decimal" currencies in Stripe (amount is already in major units)
_ZERO_DECIMAL_CURRENCIES = {
    "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG",
    "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
}

@register.filter
def stripe_amount(unit_amount, currency="eur"):
    """
    Convert Stripe integer 'unit_amount' (minor units) to a human-readable string.
    - Most currencies: 1299 -> '12.99'
    - Zero-decimal currencies (e.g. JPY): 1299 -> '1299'
    """
    if unit_amount is None:
        return ""

    try:
        amount = Decimal(str(unit_amount))
    except Exception:
        return str(unit_amount)

    currency = (currency or "").upper()
    if currency in _ZERO_DECIMAL_CURRENCIES:
        return f"{amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)}"

    major = (amount / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{major}"
