import pytest

from glassbuild.color import (
    composite,
    contrast_ratio,
    parse_rgba,
    relative_luminance,
    rgba_str,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("#FFFFFF", (255, 255, 255, 1.0)),
        ("#000", (0, 0, 0, 1.0)),
        ("#007AFF", (0, 122, 255, 1.0)),
        ("rgb(10, 20, 30)", (10, 20, 30, 1.0)),
        ("rgba(10, 20, 30, 0.5)", (10, 20, 30, 0.5)),
        ("rgba(10,20,30,.25)", (10, 20, 30, 0.25)),
        ("#3C3C4399", (60, 60, 67, 0.6)),
        ("#EBEBF561", (235, 235, 245, 0.38)),
        ("#FFFF", (255, 255, 255, 1.0)),
    ],
)
def test_parse_rgba(value, expected):
    assert parse_rgba(value) == expected


def test_parse_rgba_six_digit_hex_alpha_is_exactly_one():
    assert parse_rgba("#FFFFFF")[3] == 1.0


def test_parse_rgba_rejects_garbage():
    with pytest.raises(ValueError):
        parse_rgba("not-a-colour")


def test_rgba_str_strips_trailing_zeros():
    assert rgba_str(1, 2, 3, 0.5) == "rgba(1, 2, 3, 0.5)"
    assert rgba_str(1, 2, 3, 1.0) == "rgba(1, 2, 3, 1)"
    assert rgba_str(1, 2, 3, 0.125) == "rgba(1, 2, 3, 0.125)"


def test_composite_opaque_foreground_wins():
    assert composite((255, 0, 0, 1.0), (0, 0, 255, 1.0)) == (255, 0, 0, 1.0)


def test_composite_half_alpha_is_midpoint():
    r, g, b, a = composite((255, 255, 255, 0.5), (0, 0, 0, 1.0))
    assert (r, g, b) == (128, 128, 128)
    assert a == 1.0


def test_composite_transparent_foreground_is_noop():
    assert composite((255, 0, 0, 0.0), (0, 0, 255, 1.0)) == (0, 0, 255, 1.0)


def test_relative_luminance_endpoints():
    assert relative_luminance((0, 0, 0)) == pytest.approx(0.0)
    assert relative_luminance((255, 255, 255)) == pytest.approx(1.0)


def test_contrast_ratio_black_on_white_is_21():
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_is_order_independent():
    a = contrast_ratio((0, 0, 0), (255, 255, 255))
    b = contrast_ratio((255, 255, 255), (0, 0, 0))
    assert a == pytest.approx(b)


def test_contrast_ratio_identical_colours_is_one():
    assert contrast_ratio((80, 80, 80), (80, 80, 80)) == pytest.approx(1.0)
