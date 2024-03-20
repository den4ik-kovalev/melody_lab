import math
from enum import EnumMeta
from fractions import Fraction


class Tools:

    @staticmethod
    def fraction_gcd(x: Fraction, y: Fraction) -> Fraction:
        return Fraction(
            math.gcd(x.numerator, y.numerator),
            math.lcm(x.denominator, y.denominator)
        )

    @staticmethod
    def enum_values(enum_cls: EnumMeta):
        return [e.value for e in enum_cls]

    @staticmethod
    def reverse_dict(dct: dict):
        return {v: k for k, v in dct.items()}

    @staticmethod
    def flatten(some_list: list) -> list:
        return [x for y in some_list for x in y]
