from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def idr(value):
    amount = Decimal(str(value))
    return f"Rp{amount:,.0f}".replace(",", ".")
