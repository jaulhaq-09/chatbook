"""A generated example chat, so the app can be tried without a real export."""

from __future__ import annotations

import io
import math
import random
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.media import ffmpeg_available

# sky top, horizon, sun, three hill layers
_PALETTES = {
    "mist": ("#cfe3d8", "#f2efe0", "#fff3c4", "#8fbba3", "#5a9478", "#356650"),
    "dusk": ("#f2a98a", "#fde7c7", "#fff4d6", "#cf7f72", "#8f4e5e", "#4b2d4c"),
    "blue": ("#a5d0ee", "#eaf6ff", "#fffbe6", "#86b8dc", "#5489b9", "#31597f"),
    "gold": ("#f5c46f", "#fff0c9", "#fffaf0", "#d9a35a", "#a8743f", "#69452a"),
    "sea": ("#8fd1dc", "#f4f1e4", "#fffef2", "#eadba9", "#d3bb7c", "#b59d5a"),
    "plum": ("#b7a0e2", "#f6ddd2", "#fff1e0", "#9a86c4", "#6c5a9c", "#403468"),
}

_PHOTOS = [  # file name, width, height, palette, seed
    ("IMG-20260312-WA0001.jpg", 1200, 800, "mist", 11),
    ("IMG-20260312-WA0002.jpg", 1200, 800, "blue", 22),
    ("IMG-20260314-WA0005.jpg", 1200, 800, "gold", 33),
    ("IMG-20260314-WA0006.jpg", 1200, 800, "dusk", 44),
    ("IMG-20260314-WA0007.jpg", 1200, 800, "plum", 55),
    ("IMG-20260315-WA0008.jpg", 800, 1100, "mist", 66),
    ("IMG-20260315-WA0009.jpg", 1200, 800, "blue", 77),
    ("IMG-20260418-WA0010.jpg", 1200, 800, "sea", 88),
    ("IMG-20260418-WA0011.jpg", 1200, 800, "dusk", 99),
    ("IMG-20260418-WA0012.jpg", 800, 1100, "gold", 111),
]


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def scene(w: int, h: int, palette: str, seed: int) -> Image.Image:
    """A soft landscape: gradient sky, sun and three hill layers."""
    top, horizon, sun, *hills = (_rgb(c) for c in _PALETTES[palette])
    rnd = random.Random(seed)
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = min(1.0, y / (h * 0.65))
        draw.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, horizon, strict=True)))

    sx, sy, sr = w * (0.2 + 0.6 * rnd.random()), h * (0.2 + 0.14 * rnd.random()), min(w, h) * 0.07
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(24, 0, -1):
        r = sr * (1 + i * 0.22)
        gd.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 248, 220, 7))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=sun)

    for k, color in enumerate(hills):
        base, amp = h * (0.56 + 0.12 * k), h * (0.07 - 0.015 * k)
        f1, f2, phase = 2 + rnd.random() * 2 + k, 5 + rnd.random() * 3, rnd.random() * 6.28
        pts = [(0, h)]
        for x in range(0, w + 1, 6):
            t = x / w
            pts.append(
                (
                    x,
                    base
                    - amp * math.sin(t * f1 * math.pi + phase)
                    - amp * 0.35 * math.sin(t * f2 * math.pi + phase * 2),
                )
            )
        pts.append((w, h))
        draw.polygon(pts, fill=color)
    return img


def _jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def _video_bytes(poster: Image.Image, work: Path) -> bytes:
    """A real 2-second clip when ffmpeg can make one, otherwise a stand-in file."""
    if ffmpeg_available():
        src, out = work / "clip.jpg", work / "clip.mp4"
        poster.resize((640, 360)).save(src, "JPEG", quality=90)
        for codec in ("libx264", "mpeg4"):
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-nostdin",
                        "-v",
                        "error",
                        "-y",
                        "-loop",
                        "1",
                        "-i",
                        str(src),
                        "-t",
                        "2",
                        "-r",
                        "10",
                        "-vf",
                        "format=yuv420p",
                        "-c:v",
                        codec,
                        str(out),
                    ],
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
                return out.read_bytes()
            except (OSError, subprocess.SubprocessError):
                continue
    return b"not a real video"


def chat_text() -> str:
    lines: list[str] = []

    def add(date: str, time: str, who: str, msg: str) -> None:
        lines.append(f"{date}, {time} - {who}: {msg}")

    lines.append(
        "12/03/2026, 8:58 am - Messages and calls are end-to-end encrypted. "
        "No one outside of this chat, not even WhatsApp, can read or listen to them."
    )
    add("12/03/2026", "9:02 am", "Priya", "Good morning! Are we still on for Coorg this weekend?")
    add("12/03/2026", "9:04 am", "Arjun", "Yes! Booked the homestay last night \U0001f64c")
    add("12/03/2026", "9:04 am", "Arjun", "Check-in is Saturday at 2 pm")
    add("12/03/2026", "9:06 am", "Priya", "Perfect. Leaving at 6 from Bengaluru then?")
    add("12/03/2026", "9:09 am", "Arjun", "Plan:\n• 6:00 leave\n• 9:30 breakfast at Maddur\n• 1:00 reach Madikeri")
    add("12/03/2026", "9:11 am", "Priya", "सुबह की चाय के बिना मैं नहीं निकलूँगी \U0001f604")
    add("12/03/2026", "9:12 am", "Arjun", "Haha deal, *thermos* is packed")
    add("12/03/2026", "9:30 am", "Priya", "IMG-20260312-WA0001.jpg (file attached)\nThe view from the homestay listing")
    add("12/03/2026", "9:31 am", "Arjun", "IMG-20260312-WA0002.jpg (file attached)")
    add("12/03/2026", "9:33 am", "Priya", "Wow. We have to see the falls too")
    add("12/03/2026", "6:41 pm", "Priya", "This message was deleted")
    add("12/03/2026", "6:50 pm", "Priya", "PTT-20260312-WA0003.opus (file attached)")
    add("12/03/2026", "6:52 pm", "Arjun", "Trip-plan.pdf (file attached)")
    add("12/03/2026", "6:53 pm", "Arjun", "Sleeper bus back is ₹850 each if we decide to leave Sunday night")
    add("14/03/2026", "6:05 am", "Arjun", "Leaving now \U0001f697")
    add("14/03/2026", "8:20 am", "Priya", "VID-20260314-WA0004.mp4 (file attached)\nMist on the road!")
    add("14/03/2026", "9:41 am", "Arjun", "IMG-20260314-WA0005.jpg (file attached)")
    add("14/03/2026", "9:44 am", "Priya", "Best dosa ever. Sending the bill to you \U0001f602")
    add("14/03/2026", "1:18 pm", "Arjun", "We are at the gate. Where do we park?")
    add("14/03/2026", "1:20 pm", "Priya", "Behind the red building, the host said")
    add("14/03/2026", "2:12 pm", "Arjun", "IMG-20260314-WA0006.jpg (file attached)")
    add("14/03/2026", "2:15 pm", "Priya", "IMG-20260314-WA0007.jpg (file attached)\nOur room! Look at that balcony")
    add("14/03/2026", "7:30 pm", "Arjun", "Dinner at 8, they are making pandi curry for us")
    add(
        "15/03/2026", "7:30 am", "Priya", "IMG-20260315-WA0008.jpg (file attached)\nCoffee estate walk before breakfast"
    )
    add("15/03/2026", "11:00 am", "Arjun", "Abbey Falls was crowded but worth every step")
    add("15/03/2026", "11:02 am", "Priya", "IMG-20260315-WA0009.jpg (file attached)")
    add("15/03/2026", "6:20 pm", "Priya", "Home safe. Thank you for the best weekend ❤️")
    add("15/03/2026", "6:21 pm", "Arjun", "Same. Next one: Gokarna?")
    add("02/04/2026", "8:10 pm", "Priya", "Okay, Gokarna dates: 17 to 19 April?")
    add("02/04/2026", "8:14 pm", "Arjun", "Works for me. I will check buses")
    add("02/04/2026", "8:21 pm", "Priya", "Book it!")
    add("18/04/2026", "7:40 am", "Arjun", "IMG-20260418-WA0010.jpg (file attached)\nFirst light at Om Beach")
    add("18/04/2026", "7:42 am", "Priya", "IMG-20260418-WA0011.jpg (file attached)")
    add("18/04/2026", "7:45 am", "Priya", "IMG-20260418-WA0012.jpg (file attached)\nThis one is going in the album")
    add("18/04/2026", "7:46 am", "Arjun", "Agreed. Print it big")
    return "\n".join(lines) + "\n"


def build_sample_zip(dest: Path) -> Path:
    """Write a WhatsApp-style export (chat text plus media) to `dest` and return it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = dest.parent / f"{dest.stem}-work"
    work.mkdir(exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("WhatsApp Chat with Arjun.txt", chat_text())
            for name, w, h, palette, seed in _PHOTOS:
                zf.writestr(name, _jpeg(scene(w, h, palette, seed)))
            zf.writestr("VID-20260314-WA0004.mp4", _video_bytes(scene(1280, 720, "mist", 123), work))
            zf.writestr("PTT-20260312-WA0003.opus", b"voice note")
            zf.writestr("Trip-plan.pdf", b"%PDF-1.4 sample")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return dest
