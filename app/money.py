from decimal import ROUND_HALF_UP, Decimal


def convert_money(amount, rate):
    if amount is None or rate is None:
        return None
    return str(
        (Decimal(str(amount)) * Decimal(str(rate))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )
