"""Annotated hex listing of a decoded conversation."""

from . import fields as F
from .gloss import format_item, annotate
from .model import External, Lexical, Operation, Sentence
from .ops import OPCODES, is_cast
from .semantic import split_root


def breakdown(word):
    """Per-field breakdown of one 64-bit word, independent of context."""
    if F.is_header(word):
        st = F.field(word, F.H_QS_SHIFT, 1)
        sub = F.field(word, F.H_SUB_SHIFT, 3)
        aff, evi = F.field(word, F.H_AFF_SHIFT, 4), F.field(word, F.H_EVI_SHIFT, 3)
        return (f"class=1{st} ({'statement' if st else 'query'}) "
                f"sub={sub:03b}({(F.STATEMENT_SUBTYPES if st else F.QUERY_SUBTYPES)[sub]}) "
                f"aff={aff:04b}({F.AFFECTIONS[aff] or 'reserved'}) evi={evi:03b}({F.EVIDENTIALITY[evi] or 'reserved'}) "
                f"count={F.field(word, F.H_COUNT_SHIFT, F.H_COUNT_W)} span={F.field(word, 0, 32)}")
    if F.word_class(word) == F.CLASS_LEXICAL:
        g = lambda s, w: F.field(word, s, w)
        role = g(F.ROLE_SHIFT, 3)
        root = g(F.ROOT_SHIFT, F.ROOT_W)
        d, c, k = split_root(root)
        link = g(F.LINK_OFF_SHIFT, F.LINK_OFF_W) if g(F.LINK_FLAG_SHIFT, 1) else 0
        return (f"class=00 role={role:03b}({F.ROLE_ABBR[role] or 'reserved'}) "
                f"tmp={g(F.TEMPORAL_SHIFT, 2):02b} prg={g(F.PROGRESS_SHIFT, 2):02b} rec={g(F.RECUR_SHIFT, 2):02b} "
                f"deg={g(F.DEGREE_SHIFT, 3):03b} emp={g(F.EMPH_SHIFT, 1)} det={g(F.DET_SHIFT, 1)} "
                f"plu={g(F.PLURAL_SHIFT, 2):02b} link={'^' + str(link) if link else '-'} | "
                f"root=0x{root:08X}(dom={d},clu={c},con={k}) cat={g(0, 2):02b}({F.CATEGORIES[g(0, 2)]})")
    code = F.field(word, 56, 6)
    p = word & F.PAYLOAD_MASK
    if code == 0x3E:
        op = F.field(p, F.OP_CODE_SHIFT, 16)
        return f"class=01 type=0x7E(op) opcode=0x{op:04X}({OPCODES.get(op, ('?',))[0]}) operand=0x{p & 0xFFFFFFFF:08X}"
    return f"class=01 type=0x{0x40 | code:02X} payload=0x{p:014X}"


def dump(conv, words, lex):
    lines = []
    trace = conv._trace
    for idx, depth, item, role in trace:
        w = words[idx] if idx < len(words) else None
        pad = "  " * depth
        if role == "file":
            v = F.field(w, 48, 8)
            desc = f"FILE v{v >> 4}.{v & 0xF}, {F.field(w, 0, 40)} words follow"
        elif role.startswith("cont"):
            desc = f"  (continuation {int(role[4:]) + 1} of {item.type.name})"
        else:
            desc = f"{format_item(item, lex)}  -- {annotate(item, lex)}"
        lines.append(f"{idx:6d}  {w:016X}  {pad}{desc}")
        if not role.startswith("cont") and role != "file":
            lines.append(f"{'':6}  {'':16}  {pad}  [{breakdown(w)}]")
    return "\n".join(lines) + "\n"
