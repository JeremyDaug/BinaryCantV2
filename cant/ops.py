"""Operations (external type 0x7E): RPN operators run at read time.

Operation words never count toward a sentence's word count (doc V2.0 rule),
but they do occupy one 64-bit word of span/file length.
"""

import cmath
import math
from fractions import Fraction

from .fields import ROLES

# opcode: (name, arity, kind)
OPCODES = {
    0x0001: ("ADD", 2, "arith"), 0x0002: ("SUB", 2, "arith"), 0x0003: ("MUL", 2, "arith"),
    0x0004: ("DIV", 2, "arith"), 0x0005: ("POW", 2, "arith"), 0x0006: ("LOG", 2, "arith"),
    0x0007: ("LN", 1, "arith"), 0x0008: ("LB", 1, "arith"),
    0x0200: ("AND", 2, "logic"), 0x0201: ("OR", 2, "logic"), 0x0202: ("NOT", 1, "logic"),
    0x0203: ("NAND", 2, "logic"), 0x0204: ("NOR", 2, "logic"), 0x0205: ("XNOR", 2, "logic"),
    0x0206: ("XOR", 2, "logic"),
    0x0300: ("IF", 2, "cond"), 0x0301: ("IF_ELSE", 3, "cond"),
}
for _r, _name in enumerate(ROLES[:7]):
    OPCODES[0x0100 | _r] = ("TO_" + _name.upper(), 1, "cast")

BY_NAME = {v[0]: k for k, v in OPCODES.items()}
BY_NAME["XAND"] = BY_NAME["XNOR"]  # the doc's name for XNOR


def is_cast(opcode):
    return OPCODES.get(opcode, ("", 0, ""))[2] == "cast"


class EvalError(ValueError):
    pass


def arith(name, args):
    """Evaluate an arithmetic op on python numbers; None in -> None out."""
    if any(a is None for a in args):
        return None
    try:
        if name == "ADD":
            return args[0] + args[1]
        if name == "SUB":
            return args[0] - args[1]
        if name == "MUL":
            return args[0] * args[1]
        if name == "DIV":
            a, b = args
            if isinstance(a, int) and isinstance(b, (int, Fraction)) or isinstance(a, Fraction) and isinstance(b, (int, Fraction)):
                r = Fraction(a) / Fraction(b)
                return r.numerator if r.denominator == 1 else r
            return a / b
        if name == "POW":
            return args[0] ** args[1]
        if name == "LOG":   # x b LOG  ->  log_b(x)
            x, b = args
            return (cmath if isinstance(x, complex) else math).log(x, b)
        if name == "LN":
            return (cmath if isinstance(args[0], complex) else math).log(args[0])
        if name == "LB":
            return math.log2(args[0])
    except ZeroDivisionError:
        raise EvalError(f"{name}: division by zero") from None
    except ValueError as e:
        raise EvalError(f"{name}: {e}") from None
    raise EvalError(f"unknown arithmetic op {name}")
