"""Derivation of full, light, and lite material values from the tuning table."""

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
    """One rendered material: its fill, its rim, and its backdrop filter."""

    fill: str
    rim: str
    backdrop: str | None


_ALPHA_KEY = {"glass": "fill_alpha_glass", "frosted-glass": "fill_alpha_frosted"}


def derive(merged: dict[str, Any], material_key: str, lite: bool) -> dict[str, Material]:
    """Build the full and light materials for one material/mode combination."""
    spec = merged["material"]
    blur = int(spec["blur_px"])
    saturate = int(spec["saturate_pct"])
    rim_r, rim_g, rim_b = spec["rim_rgb"]
    rim = rgba_str(rim_r, rim_g, rim_b, float(spec["rim_alpha"]))

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
            backdrop=None if lite else f"blur({blur}px) saturate({saturate}%)",
        ),
        "light": Material(
            fill=rgba_str(base_r, base_g, base_b, light_alpha),
            rim=rim,
            backdrop=None if lite else f"blur({blur // 2}px) saturate({saturate}%)",
        ),
    }
