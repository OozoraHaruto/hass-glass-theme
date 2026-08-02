"""Derivation of full, light, and lite material values from the tuning table.

A material is three things, and each answers a different question:

- the **backdrop filter**, which decides how much of what is behind the
  surface survives to be seen through it;
- the **fill**, which tints whatever survived;
- the **edge**, which tells the eye the surface is in front of that backdrop
  rather than a hole cut through to it.

The backdrop filter runs blur first, then a chroma and luminance remap
(``saturate``/``brightness``/``contrast``). Order is not cosmetic: blurring
first turns the backdrop into a smooth field and the remap then flattens that
field toward the mode's base, so nothing behind the surface keeps enough
local contrast to compete with text sitting on it. Doing the work here is
what lets ``fill_alpha_glass`` stay low -- the alternative, raising the fill
until the backdrop stops showing through, buys the same legibility by
throwing away the translucency the theme exists for.

The edge is emitted as a pair of inset box-shadows rather than a border,
because a border can only be one colour on all four sides and a real lit edge
is not: it catches a highlight along the top and falls into shadow along the
bottom. The uniform ``rim`` is still emitted alongside it, as the perimeter
hairline; the two are complementary, not alternatives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from glassbuild.color import parse_rgba, rgba_str

LITE_FILL_ALPHA = 0.72
# The sidebar's own fill (see glassbuild/variables.py) needs a higher alpha
# than Lite's card fill: it must keep the *accent* colour (used for the
# selected nav item) above the 3:1 floor when composited over arbitrary
# dashboard content, not just body/icon text. Swept against pure black and
# pure white backdrops in both modes: 0.72 (LITE_FILL_ALPHA) drops the
# accent as low as 1.82:1; 0.90 still fails (2.88:1, light-mode-over-black);
# 0.94 is the lowest value that clears 3:1 everywhere (worst case 3.14:1).
# Deliberately a separate constant from LITE_FILL_ALPHA -- the two answer
# different questions (Lite's card fill only has to carry body text; the
# sidebar's fill also has to carry the accent) and should be free to diverge.
SIDEBAR_FILL_ALPHA = 0.94
FULL_FILL_ALPHA_FLOOR = 0.10
LIGHT_ALPHA_BONUS = 0.08


@dataclass(frozen=True)
class Material:
    """One rendered material: its fill, its rim, its edge, and its backdrop."""

    fill: str
    rim: str
    edge: str
    backdrop: str | None


_ALPHA_KEY = {
    "glass": "fill_alpha_glass",
    "frosted-glass": "fill_alpha_frosted",
    "liquid-glass": "fill_alpha_liquid",
}


def _backdrop(spec: dict[str, Any], blur: int) -> str:
    """Render one backdrop-filter chain at the given blur radius.

    Blur leads; the colour operations follow it and act on the already-blurred
    field (see the module docstring). ``blur`` is a parameter rather than read
    from ``spec`` because the light material reuses this at half radius while
    keeping every other term identical -- the remap describes the *mode*, not
    the surface's weight.
    """
    return (
        f"blur({blur}px) "
        f"saturate({int(spec['saturate_pct'])}%) "
        f"brightness({int(spec['brightness_pct'])}%) "
        f"contrast({int(spec['contrast_pct'])}%)"
    )


def _edge(spec: dict[str, Any]) -> str:
    """Render the directional specular edge as a pair of inset box-shadows.

    Highlight first, shade second, both at 1px. The pair is scaled as a unit
    by ``edge_scale`` (see tokens/frosted-glass.yaml): scaling only one half
    would tilt the implied light direction rather than soften the edge.
    """
    scale = float(spec["edge_scale"])
    hr, hg, hb = spec["highlight_rgb"]
    sr, sg, sb = spec["shade_rgb"]
    highlight = rgba_str(hr, hg, hb, round(float(spec["highlight_alpha"]) * scale, 3))
    shade = rgba_str(sr, sg, sb, round(float(spec["shade_alpha"]) * scale, 3))
    return f"inset 0 1px 0 0 {highlight}, inset 0 -1px 0 0 {shade}"


def derive(merged: dict[str, Any], material_key: str, lite: bool) -> dict[str, Material]:
    """Build the full and light materials for one material/mode combination."""
    spec = merged["material"]
    blur = int(spec["blur_px"])
    rim_r, rim_g, rim_b = spec["rim_rgb"]
    rim = rgba_str(rim_r, rim_g, rim_b, float(spec["rim_alpha"]))
    # The edge is a box-shadow, not a backdrop-filter, so Lite gets it too --
    # Lite drops the backdrop for the compositing cost on weak GPUs, and an
    # inset shadow costs none of that.
    edge = _edge(spec)

    if lite:
        base_r, base_g, base_b, _ = parse_rgba(merged["palette"]["opaque_surface"])
        full_alpha = LITE_FILL_ALPHA
    else:
        base_r, base_g, base_b = spec["fill_rgb"]
        full_alpha = float(spec[_ALPHA_KEY[material_key]])
        if full_alpha < FULL_FILL_ALPHA_FLOOR:
            raise ValueError(
                f"fill alpha {full_alpha} for {material_key} is below the "
                f"{FULL_FILL_ALPHA_FLOOR} floor"
            )

    light_alpha = min(1.0, full_alpha + LIGHT_ALPHA_BONUS)

    return {
        "full": Material(
            fill=rgba_str(base_r, base_g, base_b, full_alpha),
            rim=rim,
            edge=edge,
            backdrop=None if lite else _backdrop(spec, blur),
        ),
        "light": Material(
            fill=rgba_str(base_r, base_g, base_b, light_alpha),
            rim=rim,
            edge=edge,
            backdrop=None if lite else _backdrop(spec, blur // 2),
        ),
    }
