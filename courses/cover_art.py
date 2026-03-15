import base64
import html
from textwrap import dedent


CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 1100


GRADIENT_PRESETS = [
    {
        "key": "aurora_blush",
        "label": "Aurora Blush",
        "colors": ("#fff5fb", "#ffdce7", "#e6f6ff"),
        "title_fill": "#182a45",
        "title_stroke": "#ffffff",
    },
    {
        "key": "sky_lilac",
        "label": "Sky Prism",
        "colors": ("#d8e2ff", "#c6ddff", "#abb9ff"),
        "title_fill": "#ffffff",
        "title_stroke": "#203764",
    },
    {
        "key": "rose_mist",
        "label": "Rose Mist",
        "colors": ("#ffd6ea", "#ff96bf", "#ffe5f1"),
        "title_fill": "#ffffff",
        "title_stroke": "#6c2149",
    },
    {
        "key": "midnight_wave",
        "label": "Midnight Wave",
        "colors": ("#0d1f3d", "#1f5cb9", "#4f86ff"),
        "title_fill": "#ffffff",
        "title_stroke": "#09162c",
    },
    {
        "key": "mint_halo",
        "label": "Mint Halo",
        "colors": ("#eefcf8", "#bff3e5", "#d7fff0"),
        "title_fill": "#17324b",
        "title_stroke": "#ffffff",
    },
    {
        "key": "peach_glow",
        "label": "Peach Glow",
        "colors": ("#ffd9c5", "#ff9d84", "#ffd0b8"),
        "title_fill": "#ffffff",
        "title_stroke": "#70243a",
    },
    {
        "key": "violet_satin",
        "label": "Violet Satin",
        "colors": ("#2f3271", "#6d63da", "#d5d9ff"),
        "title_fill": "#ffffff",
        "title_stroke": "#151f55",
    },
    {
        "key": "golden_haze",
        "label": "Golden Haze",
        "colors": ("#13b7e7", "#54d8ff", "#b4e86c"),
        "title_fill": "#ffffff",
        "title_stroke": "#134d75",
    },
    {
        "key": "brand_horizon",
        "label": "Brand Horizon",
        "colors": ("#4f9d91", "#8ea45d", "#c8a03f"),
        "title_fill": "#ffffff",
        "title_stroke": "#18324a",
    },
    {
        "key": "bronze_nocturne",
        "label": "Bronze Nocturne",
        "colors": ("#111d2d", "#294563", "#9b6b22"),
        "title_fill": "#fff7eb",
        "title_stroke": "#1a2436",
    },
    {
        "key": "emerald_glass",
        "label": "Emerald Glass",
        "colors": ("#0f746b", "#28b09c", "#94efc5"),
        "title_fill": "#ffffff",
        "title_stroke": "#0c2f2b",
    },
    {
        "key": "paper_sunrise",
        "label": "Paper Sunrise",
        "colors": ("#fff6ef", "#ffe7cf", "#ffd397"),
        "title_fill": "#1a2d45",
        "title_stroke": "#fffaf4",
    },
    {
        "key": "crimson_silk",
        "label": "Crimson Silk",
        "colors": ("#ffc5d8", "#d74679", "#7c183f"),
        "title_fill": "#fff6fb",
        "title_stroke": "#4f1235",
    },
    {
        "key": "ice_circuit",
        "label": "Ice Circuit",
        "colors": ("#eef7ff", "#cae6ff", "#9bd5ff"),
        "title_fill": "#183456",
        "title_stroke": "#ffffff",
    },
    {
        "key": "noir_orchid",
        "label": "Noir Orchid",
        "colors": ("#111320", "#2f325e", "#7d49ff"),
        "title_fill": "#f8f4ff",
        "title_stroke": "#131426",
    },
]

GRADIENT_PRESET_CHOICES = [(preset["key"], preset["label"]) for preset in GRADIENT_PRESETS]
GRADIENT_PRESET_MAP = {preset["key"]: preset for preset in GRADIENT_PRESETS}


def _escape(value):
    return html.escape((value or "").strip())


def _split_title(title, max_lines=3, target_chars=16):
    words = (title or "AzureLMS").strip().split()
    if not words:
        return ["AzureLMS"]

    lines = []
    current = []
    current_length = 0

    for word in words:
        next_length = current_length + (1 if current else 0) + len(word)
        if current and next_length > target_chars and len(lines) < max_lines - 1:
            lines.append(" ".join(current))
            current = [word]
            current_length = len(word)
            continue
        current.append(word)
        current_length = next_length

    if current:
        lines.append(" ".join(current))

    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :])]

    return lines


def _title_block(title, fill, stroke, y_center):
    lines = _split_title(title)
    longest = max(len(line) for line in lines) if lines else 10
    font_size = 112
    if len(lines) == 3:
        font_size = 96
    if longest > 18:
        font_size = 88
    if longest > 24:
        font_size = 78

    total_height = font_size * 1.05 * max(len(lines) - 1, 0)
    start_y = y_center - total_height / 2
    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else font_size * 1.05
        tspans.append(
            f'<tspan x="600" dy="{dy}" dominant-baseline="middle">{_escape(line)}</tspan>'
        )

    return (
        f'<text x="600" y="{start_y:.1f}" text-anchor="middle" fill="{fill}" '
        f'stroke="{stroke}" stroke-opacity="0.16" stroke-width="1.8" paint-order="stroke fill" '
        f'font-family="Manrope, Inter, Arial, sans-serif" font-size="{font_size}" '
        f'font-weight="800" letter-spacing="-3">'
        f'{"".join(tspans)}'
        "</text>"
    )


def _kicker_block(kicker, fill):
    kicker = (kicker or "").strip()
    if not kicker:
        return ""
    return (
        f'<text x="600" y="392" text-anchor="middle" fill="{fill}" fill-opacity="0.92" '
        'font-family="Manrope, Inter, Arial, sans-serif" font-size="28" font-weight="800" '
        'letter-spacing="2.2">'
        f"{_escape(kicker).upper()}</text>"
    )


def build_cover_svg(title, preset_key="aurora_blush", kicker="", footer=""):
    preset = GRADIENT_PRESET_MAP.get(preset_key, GRADIENT_PRESET_MAP["aurora_blush"])
    color_a, color_b, color_c = preset["colors"]
    y_center = 615 if (kicker or "").strip() else 565

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" fill="none">
        <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{color_a}" />
                <stop offset="50%" stop-color="{color_b}" />
                <stop offset="100%" stop-color="{color_c}" />
            </linearGradient>
        </defs>
        <rect width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" fill="url(#bg)" />
        {_kicker_block(kicker, preset["title_fill"])}
        {_title_block(title, preset["title_fill"], preset["title_stroke"], y_center)}
    </svg>
    """
    return dedent(svg).strip()


def build_cover_data_uri(title, preset_key="aurora_blush", kicker="", footer=""):
    svg = build_cover_svg(title=title, preset_key=preset_key, kicker=kicker, footer=footer)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
