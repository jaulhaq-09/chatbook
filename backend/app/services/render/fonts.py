"""Font choices. Each key is a stack of fonts found on common systems, so nothing has to be downloaded.

The stacks name the usual Windows, macOS and Linux fonts in that order of preference. Letters a font does
not have (Devanagari, Kannada, emoji and so on) fall through to the script fonts at the end of each stack.
"""

from __future__ import annotations

_SCRIPTS = (
    '"Noto Sans Devanagari","Noto Sans Kannada","Noto Sans Tamil","Noto Sans Telugu","Noto Sans Bengali",'
    '"Noto Sans Gujarati","Noto Sans Arabic","Nirmala UI","Noto Color Emoji","Segoe UI Emoji","Apple Color Emoji"'
)

FONT_STACKS: dict[str, str] = {
    # Modern, neutral. The original look.
    "sans": f'"Noto Sans","Segoe UI","Helvetica Neue",Arial,"Liberation Sans",{_SCRIPTS},sans-serif',
    # Soft and easy to read.
    "humanist": f'"Segoe UI",Calibri,Carlito,Candara,"Noto Sans",{_SCRIPTS},sans-serif',
    # Rounded and relaxed.
    "friendly": f'"Trebuchet MS",Candara,"Lucida Grande","DejaVu Sans",{_SCRIPTS},sans-serif',
    # Wide letters, very clear on paper.
    "wide": f'Verdana,Geneva,"DejaVu Sans",{_SCRIPTS},sans-serif',
    # Classic book type.
    "serif": f'Georgia,"Times New Roman","Noto Serif","Liberation Serif",{_SCRIPTS},serif',
    # Elegant, a little old-fashioned.
    "book": f'"Palatino Linotype","Book Antiqua",Palatino,"Palatino LT STD","Noto Serif",Georgia,{_SCRIPTS},serif',
    # Typewriter.
    "mono": f'"Courier New","Courier Prime","Liberation Mono","DejaVu Sans Mono",Courier,{_SCRIPTS},monospace',
    # Handwriting.
    "hand": f'"Segoe Print","Bradley Hand","Comic Sans MS","Comic Neue","Chalkboard SE",{_SCRIPTS},cursive',
    # Flowing script, for titles only.
    "script": f'"Segoe Script","Brush Script MT","Lucida Handwriting","Apple Chancery",{_SCRIPTS},cursive',
}


def font_stack(key: str) -> str:
    return FONT_STACKS.get(key, FONT_STACKS["sans"])