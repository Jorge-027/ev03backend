from django import template

from catalog.formatting import format_clp

register = template.Library()


@register.filter
def clp(value):
    return format_clp(value)
