from decimal import Decimal, ROUND_HALF_UP


def format_clp(value):
    amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{amount:,.0f}".replace(",", ".")
