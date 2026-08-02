"""Colour parsing, compositing, and WCAG contrast maths."""

from __future__ import annotations

import re

RGBA = tuple[int, int, int, float]

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_FUNC_RE = re.compile(
    r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9]*\.?[0-9]+)\s*)?\)$"
)


def parse_rgba(value: str) -> RGBA:
    """Parse ``#RGB``, ``#RGBA``, ``#RRGGBB``, ``#RRGGBBAA``, ``rgb(...)``, or
    ``rgba(...)`` into an RGBA tuple."""
    text = value.strip()

    if _HEX_RE.match(text):
        digits = text[1:]
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits)
        alpha = round(int(digits[6:8], 16) / 255, 3) if len(digits) == 8 else 1.0
        return (
            int(digits[0:2], 16),
            int(digits[2:4], 16),
            int(digits[4:6], 16),
            alpha,
        )

    match = _FUNC_RE.match(text)
    if match:
        r, g, b, a = match.groups()
        return (int(r), int(g), int(b), float(a) if a is not None else 1.0)

    raise ValueError(f"cannot parse colour: {value!r}")


def rgba_str(r: int, g: int, b: int, a: float) -> str:
    """Render an RGBA tuple as CSS, trimming trailing zeros from the alpha."""
    alpha = f"{a:.3f}".rstrip("0").rstrip(".")
    return f"rgba({r}, {g}, {b}, {alpha or '0'})"


def composite(fg: RGBA, bg: RGBA) -> RGBA:
    """Source-over composite of ``fg`` onto ``bg``."""
    fr, fg_, fb, fa = fg
    br, bg_, bb, ba = bg
    out_a = fa + ba * (1.0 - fa)
    if out_a == 0.0:
        return (0, 0, 0, 0.0)

    def channel(f: int, b: int) -> int:
        return round((f * fa + b * ba * (1.0 - fa)) / out_a)

    return (channel(fr, br), channel(fg_, bg_), channel(fb, bb), out_a)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.1 relative luminance."""

    def linearise(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linearise(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG 2.1 contrast ratio between two opaque colours."""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
