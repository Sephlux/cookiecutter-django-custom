from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag(takes_context=True)
def org_url(context, viewname, *args, **kwargs):
    request = context["request"]
    org = getattr(request, "organization", None)
    if org and "org_slug" not in kwargs:
        kwargs["org_slug"] = org.slug
    return reverse(viewname, args=args, kwargs=kwargs)
