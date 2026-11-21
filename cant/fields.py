"""Bit-level constants for Binary Cant V2.1.

Every word is an unsigned 64-bit integer, written big-endian.  Bit 63 is the
most significant bit.  See SPEC.md for the normative description; this module
is the single source of truth the codec uses.
"""

MASK64 = (1 << 64) - 1


class CantError(ValueError):
    """Any encoding, decoding or validation error."""


def field(word, shift, width):
    """Extract an unsigned field."""
    return (word >> shift) & ((1 << width) - 1)


def put(value, shift, width, name="field"):
    """Place an unsigned value into a field, checking range."""
    if not 0 <= value < (1 << width):
        raise CantError(f"{name} value {value} does not fit in {width} bits")
    return value << shift


def signed(value, width):
    """Interpret an unsigned `width`-bit value as two's complement."""
    if value & (1 << (width - 1)):
        return value - (1 << width)
    return value


def unsigned(value, width, name="value"):
    """Encode a signed integer as `width`-bit two's complement."""
    lo, hi = -(1 << (width - 1)), (1 << (width - 1)) - 1
    if not lo <= value <= hi:
        raise CantError(f"{name} {value} out of signed {width}-bit range [{lo}, {hi}]")
    return value & ((1 << width) - 1)


# ---------------------------------------------------------------- word class
# Top two bits.  10 and 11 are both sentence headers (bit 63 = 1).
CLASS_SHIFT = 62
CLASS_LEXICAL = 0b00
CLASS_EXTERNAL = 0b01
CLASS_HEADER_QUERY = 0b10
CLASS_HEADER_STATEMENT = 0b11


def word_class(word):
    return field(word, CLASS_SHIFT, 2)


def is_header(word):
    return bool(word >> 63)


# ---------------------------------------------------------- lexical word
# High (grammar/relational) half
ROLE_SHIFT, ROLE_W = 59, 3
TEMPORAL_SHIFT, TEMPORAL_W = 57, 2
PROGRESS_SHIFT, PROGRESS_W = 55, 2
RECUR_SHIFT, RECUR_W = 53, 2
DEGREE_SHIFT, DEGREE_W = 50, 3
EMPH_SHIFT = 49
DET_SHIFT = 48
PLURAL_SHIFT, PLURAL_W = 46, 2
LINK_FLAG_SHIFT = 45
LINK_OFF_SHIFT, LINK_OFF_W = 35, 10
LEX_RESERVED_SHIFT, LEX_RESERVED_W = 32, 3
# Low (semantic) half
ROOT_SHIFT, ROOT_W = 2, 30
CAT_SHIFT, CAT_W = 0, 2

ROLES = ["Subject", "Object", "Topic", "Verb", "Modifier", "Relation", "Fusion", None]
ROLE_ABBR = ["S", "O", "T", "V", "M", "R", "F", None]
TEMPORAL = ["Timeless", "Past", "Present", "Future"]
PROGRESSION = ["Unprogressed", "Unstarted", "InProgress", "Complete"]
RECURRENCE = ["NonRecurring", "Irregular", "Continuous", "Habitual"]
DEGREE = ["Unspecified", "None", "Minimal", "Small", "Medium", "Large", "Maximal", "Total"]
PLURALITY = ["Unnumbered", "Singular", "Plural", "Numbered"]
CATEGORIES = ["obj", "rel", "act", "loc"]
CATEGORY_NAMES = ["object/abstract/state", "relation", "action", "location"]

# -------------------------------------------------------- sentence header
H_QS_SHIFT = 62           # 0 = query, 1 = statement
H_SUB_SHIFT, H_SUB_W = 59, 3
H_AFF_SHIFT, H_AFF_W = 55, 4
H_EVI_SHIFT, H_EVI_W = 52, 3
H_COUNT_SHIFT, H_COUNT_W = 32, 20
H_SPAN_SHIFT, H_SPAN_W = 0, 32

QUERY_SUBTYPES = ["Subject", "Object", "Verb", "Time", "Location", "Reasoning", "Explain", "Specify"]
STATEMENT_SUBTYPES = ["Assertion", "Deletion", "Condition", "Result", "Imperative",
                      "Exclamatory", "Uncertain", "Correction"]
AFFECTIONS = ["Honest", "Dishonest", "Happy", "Sad", "Fear", "Anger", "Anticipation",
              "Surprise", "Benevolent", "Malice", "Pain", "Pleasure", None, None, None, None]
EVIDENTIALITY = ["Direct", "Hearsay", "Expectation", "Conclusion", "Generalization",
                 "Postulate", "Opinion", None]
EVIDENTIALITY_ALIASES = {"Observation": "Direct", "Quotation": "Hearsay",
                         "Assumption": "Expectation", "Theory": "Postulate"}

# ------------------------------------------------------------- externals
EXT_TYPE_SHIFT, EXT_TYPE_W = 56, 6     # bits 61..56; top byte = 0x40 | type
PAYLOAD_W = 56
PAYLOAD_MASK = (1 << PAYLOAD_W) - 1

# Operation word (external type 0x7E)
OP_CODE_SHIFT, OP_CODE_W = 40, 16
OP_RES_SHIFT, OP_RES_W = 32, 8
OP_OPERAND_W = 32

FILE_VERSION = 0x21  # V2.1
