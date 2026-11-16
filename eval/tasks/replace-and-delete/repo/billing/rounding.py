import math

CENTS_PER_UNIT = 100


def round_price(value):
    return math.floor(value * CENTS_PER_UNIT + 0.5) / CENTS_PER_UNIT
