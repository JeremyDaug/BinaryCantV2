"""External (class 01) word types: the doc's 'outside the language' words.

Top byte of an external word = 0b01TTTTTT (0x40..0x7F); the remaining 56 bits
are the payload.  Some types are followed by continuation words (raw 64-bit
data) whose number is fixed by the head word.  A head plus its continuations
counts as ONE word in its sentence's word count (doc rule), but every 64-bit
word counts toward sentence span and file length.
"""

import math
import re
import struct
from fractions import Fraction

from .fields import PAYLOAD_MASK, field, put, signed, unsigned


class ExternalError(ValueError):
    pass


def _split_args(text):
    """Split a comma separated argument string, honouring double quotes."""
    out, cur, q, i = [], "", False, 0
    while i < len(text):
        ch = text[i]
        if q:
            if ch == "\\" and i + 1 < len(text):
                cur += ch + text[i + 1]
                i += 2
                continue
            if ch == '"':
                q = False
            cur += ch
        elif ch == '"':
            q = True
            cur += ch
        elif ch == ",":
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    if q:
        raise ExternalError("unterminated string")
    if cur.strip() or out:
        out.append(cur.strip())
    return out


def _int(s, what="value"):
    try:
        return int(s, 0)
    except (ValueError, TypeError):
        raise ExternalError(f"{what}: '{s}' is not an integer") from None


def _string(s):
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        raise ExternalError(f"expected a double-quoted string, got {s!r}")
    return bytes(s[1:-1], "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")


def _quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _nargs(args, n, name):
    if len(args) != n:
        raise ExternalError(f"{name}() takes {n} argument(s), got {len(args)}")


def _pack_bytes(data):
    words = []
    for i in range(0, len(data), 8):
        chunk = data[i:i + 8].ljust(8, b"\0")
        words.append(int.from_bytes(chunk, "big"))
    return words


def _unpack_bytes(words, length):
    raw = b"".join(w.to_bytes(8, "big") for w in words)
    if any(raw[length:]):
        raise ExternalError("non-zero padding after blob data")
    return raw[:length]


# --------------------------------------------------------------- registry
class ExtType:
    numeric = False
    def __init__(self, code, name, title):
        self.code, self.name, self.title = code, name, title

    # Overridden per type ------------------------------------------------
    def encode(self, args):            # -> (payload, [continuation words])
        raise NotImplementedError

    def n_continuations(self, payload):
        return 0

    def check(self, payload, conts):    # raise ExternalError if invalid
        pass

    def args(self, payload, conts):     # -> gloss argument string
        raise NotImplementedError

    def describe(self, payload, conts):  # -> human annotation
        return f"{self.title}: {self.args(payload, conts)}"

    def value(self, payload, conts):    # python value for evaluation, if numeric
        return None


REGISTRY = {}
BY_NAME = {}


def register(cls, code, name, title, **kw):
    t = cls(code, name, title)
    for k, v in kw.items():
        setattr(t, k, v)
    REGISTRY[code] = t
    BY_NAME[name] = t
    return t


# ---- control ---------------------------------------------------------------
class FileHeader(ExtType):
    def encode(self, args):
        raise ExternalError("file() headers are written by the encoder, not by hand")
    def check(self, payload, conts):
        if field(payload, 40, 8):
            raise ExternalError("file header reserved bits 47..40 must be zero")
    def args(self, payload, conts):
        v = field(payload, 48, 8)
        return f"v{v >> 4}.{v & 0xF}, length={field(payload, 0, 40)}"


class Party(ExtType):
    """SPEAKER / LISTENER marker: payload = 56-bit ID (0 = Narrator / everyone)."""
    def encode(self, args):
        _nargs(args, 1, self.name)
        v = _int(args[0], self.name)
        return put(v, 0, 56, f"{self.name} id"), []
    def args(self, payload, conts):
        return str(payload)
    def describe(self, payload, conts):
        if payload == 0:
            return f"{self.title}: " + ("Narrator" if self.name == "speaker" else "everyone")
        return f"{self.title}: id {payload}"


# ---- numbers ---------------------------------------------------------------
class Int56(ExtType):
    numeric = True
    def encode(self, args):
        _nargs(args, 1, self.name)
        return unsigned(_int(args[0]), 56, "int"), []
    def value(self, p, c):
        return signed(p, 56)
    def args(self, p, c):
        return str(self.value(p, c))


class Float32(ExtType):
    numeric = True
    def encode(self, args):
        _nargs(args, 1, self.name)
        try:
            bits = struct.unpack(">I", struct.pack(">f", float(args[0])))[0]
        except (ValueError, OverflowError) as e:
            raise ExternalError(f"float32: {e}") from None
        return bits, []
    def check(self, p, c):
        if p >> 32:
            raise ExternalError("float32 payload bits 55..32 must be zero")
    def value(self, p, c):
        return struct.unpack(">f", struct.pack(">I", p & 0xFFFFFFFF))[0]
    def args(self, p, c):
        return repr(self.value(p, c))


class Float64(ExtType):
    numeric = True
    def encode(self, args):
        _nargs(args, 1, self.name)
        return 0, [struct.unpack(">Q", struct.pack(">d", float(args[0])))[0]]
    def n_continuations(self, p):
        return 1
    def check(self, p, c):
        if p:
            raise ExternalError("float64 head payload must be zero")
    def value(self, p, c):
        return struct.unpack(">d", struct.pack(">Q", c[0]))[0]
    def args(self, p, c):
        return repr(self.value(p, c))


class Complex56(ExtType):
    numeric = True
    def encode(self, args):
        _nargs(args, 2, self.name)
        return (unsigned(_int(args[0]), 28, "real") << 28) | unsigned(_int(args[1]), 28, "imag"), []
    def value(self, p, c):
        return complex(signed(field(p, 28, 28), 28), signed(field(p, 0, 28), 28))
    def args(self, p, c):
        v = self.value(p, c)
        return f"{int(v.real)},{int(v.imag)}"


class Rational56(ExtType):
    numeric = True
    def encode(self, args):
        _nargs(args, 1, self.name)
        m = re.fullmatch(r"\s*(-?)(\d+)\s*/\s*(\d+)\s*", args[0])
        if not m:
            raise ExternalError("rational() takes 'n/d', e.g. rational(-3/4)")
        neg, n, d = m.group(1) == "-", int(m.group(2)), int(m.group(3))
        if d == 0:
            raise ExternalError("rational denominator must be non-zero")
        return put(int(neg), 55, 1) | put(n, 28, 27, "numerator") | put(d, 0, 28, "denominator"), []
    def check(self, p, c):
        if field(p, 0, 28) == 0:
            raise ExternalError("rational denominator must be non-zero")
    def value(self, p, c):
        v = Fraction(field(p, 28, 27), field(p, 0, 28))
        return -v if p >> 55 else v
    def args(self, p, c):
        return f"{'-' if p >> 55 else ''}{field(p, 28, 27)}/{field(p, 0, 28)}"


class BigInt(ExtType):
    numeric = True
    def encode(self, args):
        _nargs(args, 1, self.name)
        v = _int(args[0])
        n = max(1, (v.bit_length() + 1 + 63) // 64)
        raw = (v & ((1 << (64 * n)) - 1)).to_bytes(8 * n, "big")
        return n, _pack_bytes(raw)
    def n_continuations(self, p):
        return p & 0xFFFFFFFF
    def check(self, p, c):
        if p >> 32:
            raise ExternalError("bigint payload bits 55..32 must be zero")
        if (p & 0xFFFFFFFF) == 0:
            raise ExternalError("bigint needs at least one continuation word")
    def value(self, p, c):
        raw = b"".join(w.to_bytes(8, "big") for w in c)
        return int.from_bytes(raw, "big", signed=True)
    def args(self, p, c):
        return str(self.value(p, c))


# ---- colours ---------------------------------------------------------------
class Color(ExtType):
    channels, width = 3, 8
    def encode(self, args):
        if len(args) == 1 and re.fullmatch(r"#?[0-9A-Fa-f]+", args[0]) and self.width == 8:
            h = args[0].lstrip("#")
            if len(h) != 2 * self.channels:
                raise ExternalError(f"{self.name}() hex form needs {2 * self.channels} hex digits")
            vals = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
        else:
            _nargs(args, self.channels, self.name)
            vals = [_int(a, "channel") for a in args]
        p = 0
        for v in vals:
            p = (p << self.width) | put(v, 0, self.width, "channel")
        return p, []
    def check(self, p, c):
        if p >> (self.channels * self.width):
            raise ExternalError(f"{self.name} unused high payload bits must be zero")
    def _vals(self, p):
        return [field(p, self.width * (self.channels - 1 - i), self.width) for i in range(self.channels)]
    def args(self, p, c):
        if self.width == 8:
            return "#" + "".join(f"{v:02X}" for v in self._vals(p))
        return ",".join(str(v) for v in self._vals(p))


# ---- direction -------------------------------------------------------------
FRAMES = ["speaker", "listener", "subject", "object"]


class Direction(ExtType):
    """dir(yaw, pitch, roll[, relative][, to][, frame=F]) - angles in steps of tau/65536."""
    def encode(self, args):
        if len(args) < 3:
            raise ExternalError("dir() needs yaw,pitch,roll (steps of tau/65536) then optional flags")
        y, pi, r = (_int(a, "angle") for a in args[:3])
        rel, to, frame = 0, 0, 0
        for a in args[3:]:
            if a == "relative":
                rel = 1
            elif a == "to":
                to = 1
            elif a == "from":
                to = 0
            elif a.startswith("frame="):
                f = a[6:]
                if f not in FRAMES:
                    raise ExternalError(f"frame must be one of {FRAMES}")
                frame = FRAMES.index(f)
            else:
                raise ExternalError(f"unknown dir() flag '{a}'")
        if frame and not rel:
            raise ExternalError("a frame only applies to relative directions")
        return (rel << 55) | (to << 54) | (frame << 52) | put(y, 32, 16, "yaw") | put(pi, 16, 16, "pitch") | put(r, 0, 16, "roll"), []
    def check(self, p, c):
        if field(p, 48, 4):
            raise ExternalError("direction reserved bits 51..48 must be zero")
        if field(p, 52, 2) and not p >> 55:
            raise ExternalError("direction frame set on an objective direction")
    def args(self, p, c):
        s = f"{field(p, 32, 16)},{field(p, 16, 16)},{field(p, 0, 16)}"
        if p >> 55:
            s += ",relative"
        if field(p, 54, 1):
            s += ",to"
        if field(p, 52, 2):
            s += ",frame=" + FRAMES[field(p, 52, 2)]
        return s
    def describe(self, p, c):
        deg = [field(p, s, 16) * 360 / 65536 for s in (32, 16, 0)]
        return (f"direction {'relative to ' + FRAMES[field(p, 52, 2)] if p >> 55 else 'objective'}, "
                f"{'to' if field(p, 54, 1) else 'from'}, yaw/pitch/roll = "
                + "/".join(f"{d:.4g}°" for d in deg))


# ---- chemistry -------------------------------------------------------------
class Atom(ExtType):
    def encode(self, args):
        _nargs(args, 3, self.name)
        pr, n, e = (_int(a) for a in args)
        return put(pr, 40, 16, "protons") | put(n, 24, 16, "neutrons") | put(e, 8, 16, "electrons"), []
    def check(self, p, c):
        if p & 0xFF:
            raise ExternalError("atom reserved bits 7..0 must be zero")
    def args(self, p, c):
        return f"{field(p, 40, 16)},{field(p, 24, 16)},{field(p, 8, 16)}"
    def describe(self, p, c):
        return f"atom P={field(p, 40, 16)} N={field(p, 24, 16)} E={field(p, 8, 16)}"


BONDS = ["ionic", "covalent", "metallic", "none"]


class Compound(ExtType):
    """compound(node; node; ...) where node = P/N/children/bond/count[/bond2/count2].

    Nodes are listed in pre-order; `children` is the node's child count; the
    first bond describes the bond to the parent (must be none/0 for the root),
    the optional second bond is a secondary bond to the previous sibling.
    N = 65535 means 'natural isotope mix'.
    """
    def encode(self, args):
        text = ",".join(args)
        nodes = [n.strip() for n in text.split(";") if n.strip()]
        if not nodes:
            raise ExternalError("compound() needs at least one node")
        words = []
        for n in nodes:
            parts = n.split("/")
            if len(parts) not in (5, 7):
                raise ExternalError(f"compound node '{n}' must be P/N/children/bond/count[/bond2/count2]")
            if len(parts) == 5:
                parts += ["none", "0"]
            pr, nn, ch = _int(parts[0]), _int(parts[1]), _int(parts[2])
            b1, c1, b2, c2 = parts[3], _int(parts[4]), parts[5], _int(parts[6])
            for b in (b1, b2):
                if b not in BONDS:
                    raise ExternalError(f"bond type '{b}' must be one of {BONDS}")
            words.append((BONDS.index(b1) << 62) | put(c1, 58, 4, "bond count") | (BONDS.index(b2) << 56)
                         | put(c2, 52, 4, "bond count") | put(ch, 44, 8, "children")
                         | put(pr, 16, 16, "protons") | put(nn, 0, 16, "neutrons"))
        self.check(len(words), words)
        return len(words), words
    def n_continuations(self, p):
        return p
    def check(self, p, c):
        if p == 0:
            raise ExternalError("a compound has at least one node")
        for w in c:
            if field(w, 32, 12):
                raise ExternalError("compound node reserved bits 43..32 must be zero")
        need = 1
        for i, w in enumerate(c):
            if need == 0:
                raise ExternalError("compound tree is complete before its last node")
            need += field(w, 44, 8) - 1
            if i == 0 and (field(w, 62, 2) != 3 or field(w, 58, 4)):
                raise ExternalError("compound root node cannot have a parent bond")
        if need != 0:
            raise ExternalError(f"compound tree incomplete: {need} child node(s) missing")
    def _node(self, w):
        s = f"{field(w, 16, 16)}/{field(w, 0, 16)}/{field(w, 44, 8)}/{BONDS[field(w, 62, 2)]}/{field(w, 58, 4)}"
        if field(w, 56, 2) != 3 or field(w, 52, 4):
            s += f"/{BONDS[field(w, 56, 2)]}/{field(w, 52, 4)}"
        return s
    def args(self, p, c):
        return "; ".join(self._node(w) for w in c)


# ---- time ------------------------------------------------------------------
class Seconds(ExtType):
    def encode(self, args):
        _nargs(args, 1, self.name)
        return unsigned(_int(args[0]), 56, self.name), []
    def args(self, p, c):
        return str(signed(p, 56))
    def describe(self, p, c):
        v = signed(p, 56)
        if self.name == "time":
            import datetime
            try:
                t = datetime.datetime.fromtimestamp(v, datetime.timezone.utc).isoformat()
            except (OverflowError, OSError, ValueError):
                t = "out of calendar range"
            return f"time {v} s since 1970-01-01T00:00:00Z ({t})"
        return f"duration {v} s"


class DateTime(ExtType):
    RX = re.compile(r"(-?\d+)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(Z|[+-]\d\d:\d\d)")
    def encode(self, args):
        _nargs(args, 1, self.name)
        m = self.RX.fullmatch(args[0])
        if not m:
            raise ExternalError("datetime() takes YYYY-MM-DDTHH:MM:SS(Z|+HH:MM)")
        y, mo, d, h, mi, s = (int(g) for g in m.groups()[:6])
        z = m.group(7)
        off = 0
        if z != "Z":
            sign = -1 if z[0] == "-" else 1
            hh, mm = int(z[1:3]), int(z[4:6])
            if mm % 15:
                raise ExternalError("UTC offset must be a multiple of 15 minutes")
            off = sign * (hh * 4 + mm // 15)
        p = (unsigned(y, 20, "year") << 36) | put(mo, 32, 4, "month") | put(d, 27, 5, "day") \
            | put(h, 22, 5, "hour") | put(mi, 16, 6, "minute") | put(s, 10, 6, "second") | (unsigned(off, 7, "offset") << 3)
        self.check(p, [])
        return p, []
    def check(self, p, c):
        mo, d, h, mi, s = field(p, 32, 4), field(p, 27, 5), field(p, 22, 5), field(p, 16, 6), field(p, 10, 6)
        if not (1 <= mo <= 12 and 1 <= d <= 31 and h < 24 and mi < 60 and s <= 60):
            raise ExternalError("datetime field out of range")
        if p & 0b111:
            raise ExternalError("datetime reserved bits 2..0 must be zero")
    def args(self, p, c):
        y = signed(field(p, 36, 20), 20)
        off = signed(field(p, 3, 7), 7) * 15
        z = "Z" if off == 0 else f"{'-' if off < 0 else '+'}{abs(off) // 60:02d}:{abs(off) % 60:02d}"
        return (f"{y:04d}-{field(p, 32, 4):02d}-{field(p, 27, 5):02d}T{field(p, 22, 5):02d}:"
                f"{field(p, 16, 6):02d}:{field(p, 10, 6):02d}{z}")


class TimeNs(ExtType):
    def encode(self, args):
        _nargs(args, 1, self.name)
        return 0, [unsigned(_int(args[0]), 64, "nanoseconds")]
    def n_continuations(self, p):
        return 1
    def check(self, p, c):
        if p:
            raise ExternalError("time_ns head payload must be zero")
    def args(self, p, c):
        return str(signed(c[0], 64))


# ---- references / identity ------------------------------------------------
class Plain56(ExtType):
    def encode(self, args):
        _nargs(args, 1, self.name)
        return put(_int(args[0]), 0, 56, self.name), []
    def args(self, p, c):
        return str(p)


class Coordinate(ExtType):
    UNIT = 360 / (1 << 28)
    def encode(self, args):
        _nargs(args, 2, self.name)
        try:
            lat, lon = float(args[0]), float(args[1])
        except ValueError:
            raise ExternalError("coord() takes decimal degrees lat,lon") from None
        if not (-90 <= lat <= 90 and -180 <= lon < 180):
            raise ExternalError("coord() latitude must be in [-90, 90], longitude in [-180, 180)")
        return (unsigned(round(lat / self.UNIT), 28, "lat") << 28) | unsigned(round(lon / self.UNIT), 28, "lon"), []
    def args(self, p, c):
        return f"{signed(field(p, 28, 28), 28) * self.UNIT:.7f},{signed(field(p, 0, 28), 28) * self.UNIT:.7f}"


class Blob(ExtType):
    """Length-prefixed byte inclusion: tag(8) | reserved(16) | byte length(32), then data words."""
    text = False
    tags = None
    def encode(self, args):
        if self.text:
            _nargs(args, 1, self.name)
            data, tag = _string(args[0]).encode("utf-8"), 0
        else:
            _nargs(args, 2, self.name)
            t = args[0]
            if self.tags and t in self.tags:
                tag = self.tags.index(t)
            else:
                tag = _int(t, "tag")
            h = args[1]
            if h.startswith('"'):
                data = _string(h).encode("utf-8")
            else:
                try:
                    data = bytes.fromhex(h)
                except ValueError:
                    raise ExternalError("blob data must be hex or a quoted string") from None
        return put(tag, 48, 8, "tag") | put(len(data), 0, 32, "length"), _pack_bytes(data)
    def n_continuations(self, p):
        return (field(p, 0, 32) + 7) // 8
    def check(self, p, c):
        if field(p, 32, 16):
            raise ExternalError(f"{self.name} reserved bits 47..32 must be zero")
        if self.text and field(p, 48, 8):
            raise ExternalError(f"{self.name} tag must be 0 (UTF-8)")
        data = _unpack_bytes(c, field(p, 0, 32))
        if self.text:
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                raise ExternalError(f"{self.name} data is not valid UTF-8") from None
    def args(self, p, c):
        data = _unpack_bytes(c, field(p, 0, 32))
        if self.text:
            return _quote(data.decode("utf-8"))
        tag = field(p, 48, 8)
        t = self.tags[tag] if self.tags and tag < len(self.tags) else str(tag)
        return f"{t},{data.hex()}"


class Char(ExtType):
    def encode(self, args):
        _nargs(args, 1, self.name)
        a = args[0]
        if a.startswith("U+"):
            cp = int(a[2:], 16)
        else:
            s = _string(a)
            if len(s) != 1:
                raise ExternalError("char() takes exactly one character")
            cp = ord(s)
        if cp > 0x10FFFF:
            raise ExternalError("not a Unicode code point")
        return cp, []
    def check(self, p, c):
        if p > 0x10FFFF:
            raise ExternalError("char payload is not a Unicode code point")
    def args(self, p, c):
        return f"U+{p:04X}"


register(FileHeader, 0x00, "file", "conversation file header")
register(Party, 0x01, "speaker", "speaker")
register(Party, 0x02, "listener", "listener")
register(Int56, 0x08, "int", "integer (signed 56-bit)")
register(Float32, 0x09, "float", "float (IEEE-754 binary32)")
register(Float64, 0x0A, "float64", "float (IEEE-754 binary64, +1 word)")
register(Complex56, 0x0B, "complex", "complex (2 x signed 28-bit)")
register(Rational56, 0x0C, "rational", "rational (sign, 27-bit num, 28-bit den)")
register(BigInt, 0x0D, "bigint", "big integer (+n words)")
register(Color, 0x10, "rgb", "colour RGB", channels=3, width=8)
register(Color, 0x11, "rgba", "colour RGBA", channels=4, width=8)
register(Color, 0x12, "hsl", "colour HSL", channels=3, width=8)
register(Color, 0x13, "yuv", "colour YUV", channels=3, width=8)
register(Color, 0x14, "ycbcr", "colour YCbCr", channels=3, width=8)
register(Color, 0x15, "rgba14", "colour RGBA, 14 bits/channel", channels=4, width=14)
register(Direction, 0x18, "dir", "direction")
register(Atom, 0x20, "atom", "atom")
register(Compound, 0x21, "compound", "compound (+n node words)")
register(Seconds, 0x28, "time", "time (s since Unix epoch)")
register(Seconds, 0x29, "duration", "duration (s)")
register(DateTime, 0x2A, "datetime", "formatted date-time")
register(TimeNs, 0x2B, "time_ns", "time (ns since Unix epoch, +1 word)")
register(Plain56, 0x30, "ptr", "pointer (absolute word index in file)")
register(Plain56, 0x32, "id", "ID (specific name)")
register(Blob, 0x33, "sig", "signature (+n words)", tags=["unspecified", "ed25519", "ecdsa-p256", "hmac-sha256"])
register(Coordinate, 0x34, "coord", "coordinate (lat, lon)")
register(Blob, 0x35, "uri", "URI (+n words)", text=True)
register(Blob, 0x38, "text", "text, UTF-8 (+n words)", text=True)
register(Blob, 0x39, "bytes", "raw bytes (+n words)", tags=["raw", "png", "jpeg", "gif", "webp"])
register(Char, 0x3A, "char", "character (Unicode code point)")

OPERATION_CODE = 0x3E
CONTROL_CODES = {0x00, 0x01, 0x02}
NUMERIC_CODES = {c for c, t in REGISTRY.items() if t.numeric}


def ext_word(code, payload):
    return (0b01 << 62) | (code << 56) | (payload & PAYLOAD_MASK)
