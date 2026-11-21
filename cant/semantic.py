"""Semantic half of a lexical word: 30-bit root + 2-bit category.

Root layout (V2.1 'semantic locality' scheme, see SPEC.md section 9):

    bits 29..22  domain   (8 bits)  - one of 16 codewords of RM(1,3), min distance 4
    bits 21..14  cluster  (8 bits)  - one of 16 codewords of RM(1,3), min distance 4
    bits 13..0   concept  (14 bits) - Gray-coded sibling index (neighbours differ by 1 bit)

Category (bits 1..0): 00 object/abstract/state, 01 relation, 10 action, 11 location.
"""

from .fields import CATEGORIES

DOMAIN_SHIFT, CLUSTER_SHIFT, CONCEPT_SHIFT = 22, 14, 0
DOMAIN_W, CLUSTER_W, CONCEPT_W = 8, 8, 14

# First-order Reed-Muller code RM(1,3) = extended Hamming [8,4,4], sorted.
# Any two distinct codewords differ in at least 4 bits (0x00/0xFF differ in 8).
RM13 = [0x00, 0x0F, 0x33, 0x3C, 0x55, 0x5A, 0x66, 0x69,
        0x96, 0x99, 0xA5, 0xAA, 0xC3, 0xCC, 0xF0, 0xFF]

DOMAINS = {
    0: "core (null, existence, deixis, possession)",
    1: "body (organs, effectors, sensors)",
    2: "beings (kinds of entity)",
    3: "social (kinship, guidance, affiliation)",
    4: "artifacts (made things)",
    5: "arts (music, performance)",
    6: "qualities (magnitudes, measures)",
    7: "mind (affect, cognition, hedonic states)",
    8: "motion and transfer",
    9: "making and change",
    10: "places and nature",
    11: "time",
    12: "quantity",
    13: "spatial relations",
    14: "events and manner",
    15: "totality (everything)",
}


def gray(n):
    return n ^ (n >> 1)


def gray_inverse(g):
    n = 0
    while g:
        n ^= g
        g >>= 1
    return n


def make_root(domain, cluster, concept):
    """Build a 30-bit root from domain index, cluster index and concept index."""
    if not 0 <= domain < 16 or not 0 <= cluster < 16:
        raise ValueError("domain and cluster indices must be 0..15")
    if not 0 <= concept < (1 << CONCEPT_W):
        raise ValueError("concept index must be 0..16383")
    return (RM13[domain] << DOMAIN_SHIFT) | (RM13[cluster] << CLUSTER_SHIFT) | gray(concept)


def split_root(root):
    """Return (domain_idx|None, cluster_idx|None, concept_idx) for a 30-bit root.

    None means the field value is not a codeword (extension / unassigned space).
    """
    d = (root >> DOMAIN_SHIFT) & 0xFF
    c = (root >> CLUSTER_SHIFT) & 0xFF
    k = root & ((1 << CONCEPT_W) - 1)
    return (RM13.index(d) if d in RM13 else None,
            RM13.index(c) if c in RM13 else None,
            gray_inverse(k))


def semantic(root, category):
    if not 0 <= root < (1 << 30):
        raise ValueError(f"root 0x{root:x} does not fit in 30 bits")
    return (root << 2) | category


def category_index(name):
    try:
        return CATEGORIES.index(name)
    except ValueError:
        raise ValueError(f"unknown category '{name}' (use one of {', '.join(CATEGORIES)})") from None


def hamming(a, b):
    return bin(a ^ b).count("1")


def tree_distance(a, b):
    """Prefix-tree distance between two 32-bit semantic halves.

    0 = same sense, 1 = same root (sibling sense), 2 = same cluster,
    3 = same domain, 4 = different domain.
    """
    if a == b:
        return 0
    ra, rb = a >> 2, b >> 2
    if ra == rb:
        return 1
    if ra >> CLUSTER_SHIFT == rb >> CLUSTER_SHIFT:
        return 2
    if ra >> DOMAIN_SHIFT == rb >> DOMAIN_SHIFT:
        return 3
    return 4
