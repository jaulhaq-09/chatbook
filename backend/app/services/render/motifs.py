# ruff: noqa: E501
"""Small decorations for the empty space on the cover and back page.

Each motif is an SVG drawn in the two chosen colours. Colours are validated hex strings (see schemas), so
the markup can be placed in the page as it is.
"""

from __future__ import annotations

import math

MOTIFS = ("none", "bubbles", "dots", "waves", "rings", "hearts", "sparkles")
_HEART = "M0 -1.5 C -2.5 -5.5, -8 -3, -5.5 1 L 0 6.5 L 5.5 1 C 8 -3, 2.5 -5.5, 0 -1.5 Z"
_SPARK = "M0 -6 Q 1 -1 6 0 Q 1 1 0 6 Q -1 1 -6 0 Q -1 -1 0 -6 Z"


def _svg(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 44" width="100%" height="100%" '
        f'preserveAspectRatio="xMidYMid meet" aria-hidden="true">{body}</svg>'
    )


def _bubble(x: float, y: float, w: float, fill: str, left: bool, lines: tuple[float, float]) -> str:
    tail = (
        f"M{x + 6} {y + 11} L{x + 4} {y + 15.5} L{x + 12} {y + 11} Z"
        if left
        else f"M{x + w - 6} {y + 11} L{x + w - 4} {y + 15.5} L{x + w - 12} {y + 11} Z"
    )
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="11.5" rx="5.7" fill="{fill}"/>'
        f'<path d="{tail}" fill="{fill}"/>'
        f'<rect x="{x + 5}" y="{y + 3.2}" width="{lines[0]}" height="1.9" rx=".95" fill="#fff" opacity=".92"/>'
        f'<rect x="{x + 5}" y="{y + 6.6}" width="{lines[1]}" height="1.9" rx=".95" fill="#fff" opacity=".7"/>'
    )


def _bubbles(c1: str, c2: str) -> str:
    return _svg(
        _bubble(6, 1, 50, c1, True, (34, 20))
        + _bubble(60, 14, 54, c2, False, (38, 26))
        + _bubble(6, 28, 38, c1, True, (24, 14))
        + f'<circle cx="104" cy="38" r="3.2" fill="{c2}" opacity=".35"/>'
        + f'<circle cx="112" cy="38" r="2" fill="{c2}" opacity=".25"/>'
    )


def _dots(c1: str, c2: str) -> str:
    out = []
    cols, rows = 24, 8
    for r in range(rows):
        for c in range(cols):
            x, y = 5 + c * 4.55, 4 + r * 5
            d = math.hypot((c - cols / 2) / (cols / 2), (r - rows / 2) / (rows / 2))
            radius = max(0.35, 2.0 * (1 - d * 0.75))
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.2f}" fill="{c1 if (c + r) % 2 == 0 else c2}" opacity="{0.9 - d * 0.5:.2f}"/>'
            )
    return _svg("".join(out))


def _waves(c1: str, c2: str) -> str:
    path = "M0 22 C 15 6, 30 6, 45 22 S 75 38, 90 22 S 112 8, 120 16"
    return _svg(
        f'<path d="{path}" transform="translate(0 -9)" fill="none" stroke="{c2}" stroke-width="2.2" stroke-linecap="round" opacity=".55"/>'
        f'<path d="{path}" fill="none" stroke="{c1}" stroke-width="2.6" stroke-linecap="round"/>'
        f'<path d="{path}" transform="translate(0 9)" fill="none" stroke="{c2}" stroke-width="2.2" stroke-linecap="round" opacity=".8"/>'
    )


def _rings(c1: str, c2: str) -> str:
    return _svg(
        f'<circle cx="38" cy="22" r="17" fill="none" stroke="{c1}" stroke-width="1.8"/>'
        f'<circle cx="60" cy="22" r="17" fill="none" stroke="{c2}" stroke-width="1.8"/>'
        f'<circle cx="82" cy="22" r="17" fill="none" stroke="{c1}" stroke-width="1.8" opacity=".6"/>'
        f'<circle cx="49" cy="22" r="4" fill="{c2}" opacity=".85"/>'
        f'<circle cx="71" cy="22" r="4" fill="{c1}" opacity=".85"/>'
    )


def _scatter(shape: str, c1: str, c2: str, spots: list[tuple[float, float, float]]) -> str:
    out = []
    for i, (x, y, s) in enumerate(spots):
        colour = c1 if i % 2 == 0 else c2
        out.append(
            f'<path d="{shape}" transform="translate({x} {y}) scale({s})" fill="{colour}" opacity="{0.95 if s > 1 else 0.6}"/>'
        )
    return _svg("".join(out))


def _hearts(c1: str, c2: str) -> str:
    spots = [
        (20, 14, 2.2),
        (46, 28, 1.4),
        (60, 12, 3.0),
        (78, 30, 1.8),
        (98, 16, 2.0),
        (34, 36, 0.9),
        (88, 38, 1.0),
        (108, 30, 0.8),
        (8, 30, 1.0),
    ]
    return _scatter(_HEART, c1, c2, spots)


def _sparkles(c1: str, c2: str) -> str:
    spots = [
        (18, 12, 2.0),
        (42, 30, 1.5),
        (60, 14, 2.8),
        (82, 28, 1.7),
        (102, 12, 1.8),
        (30, 36, 0.9),
        (72, 40, 0.8),
        (112, 32, 1.0),
    ]
    dots = f'<circle cx="50" cy="8" r="1.1" fill="{c2}" opacity=".6"/><circle cx="92" cy="22" r="1.3" fill="{c1}" opacity=".5"/><circle cx="12" cy="30" r="1.2" fill="{c2}" opacity=".5"/>'
    return _scatter(_SPARK, c1, c2, spots).replace("</svg>", dots + "</svg>")


_BUILDERS = {
    "bubbles": _bubbles,
    "dots": _dots,
    "waves": _waves,
    "rings": _rings,
    "hearts": _hearts,
    "sparkles": _sparkles,
}


def motif_svg(kind: str, c1: str, c2: str) -> str:
    """SVG markup for the motif, or an empty string for "none"."""
    build = _BUILDERS.get(kind)
    return build(c1, c2) if build else ""