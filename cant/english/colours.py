"""Colour words <-> rgb() externals."""

COLOURS = {
    "red": "#FF0000", "green": "#008000", "blue": "#0000FF", "yellow": "#FFFF00", "black": "#000000",
    "white": "#FFFFFF", "orange": "#FFA500", "purple": "#800080", "brown": "#8B4513", "gray": "#808080",
    "grey": "#808080", "pink": "#FFC0CB", "gold": "#FFD700", "silver": "#C0C0C0",
}
CANONICAL = [c for c in COLOURS if c != "grey"]


def nearest(hexstr):
    """Closest colour word to '#RRGGBB'; returns (word, exact)."""
    h = hexstr.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    best, dist = None, None
    for name in CANONICAL:
        c = COLOURS[name].lstrip("#")
        v = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
        d = sum((a - b) ** 2 for a, b in zip(rgb, v))
        if dist is None or d < dist:
            best, dist = name, d
    return best, dist == 0
