import base64
import html
from textwrap import dedent


CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 1100


GRADIENT_PRESETS = [
    {"key": "aurora_blush", "label": "Aurora Blush", "renderer": "aurora_blush"},
    {"key": "sky_lilac", "label": "Sky Prism", "renderer": "sky_lilac"},
    {"key": "rose_mist", "label": "Rose Mist", "renderer": "rose_mist"},
    {"key": "midnight_wave", "label": "Midnight Wave", "renderer": "midnight_wave"},
    {"key": "mint_halo", "label": "Mint Halo", "renderer": "mint_halo"},
    {"key": "peach_glow", "label": "Peach Glow", "renderer": "peach_glow"},
    {"key": "violet_satin", "label": "Violet Satin", "renderer": "violet_satin"},
    {"key": "golden_haze", "label": "Golden Haze", "renderer": "golden_haze"},
    {"key": "brand_horizon", "label": "Brand Horizon", "renderer": "brand_horizon"},
    {"key": "bronze_nocturne", "label": "Bronze Nocturne", "renderer": "bronze_nocturne"},
    {"key": "emerald_glass", "label": "Emerald Glass", "renderer": "emerald_glass"},
    {"key": "paper_sunrise", "label": "Paper Sunrise", "renderer": "paper_sunrise"},
    {"key": "crimson_silk", "label": "Crimson Silk", "renderer": "crimson_silk"},
    {"key": "ice_circuit", "label": "Ice Circuit", "renderer": "ice_circuit"},
    {"key": "noir_orchid", "label": "Noir Orchid", "renderer": "noir_orchid"},
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

    last_line = lines[-1]
    if len(last_line) > target_chars + 6 and len(lines) < max_lines:
        pivot = max(1, len(last_line) // 2)
        parts = last_line.split()
        mid = max(1, len(parts) // 2)
        lines = lines[:-1] + [" ".join(parts[:mid]), " ".join(parts[mid:])]
        lines = lines[:max_lines]

    return lines


def _title_block(title, fill, stroke):
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
    start_y = 565 - total_height / 2
    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else font_size * 1.05
        tspans.append(
            f'<tspan x="600" dy="{dy}" dominant-baseline="middle">{_escape(line)}</tspan>'
        )

    return (
        f'<text x="600" y="{start_y:.1f}" text-anchor="middle" fill="{fill}" '
        f'stroke="{stroke}" stroke-opacity="0.18" stroke-width="2" paint-order="stroke fill" '
        f'font-family="Manrope, Inter, Arial, sans-serif" font-size="{font_size}" '
        f'font-weight="800" letter-spacing="-3">'
        f'{"".join(tspans)}'
        "</text>"
    )


def _badge_block(kicker, fill, text_fill):
    kicker = (kicker or "").strip()
    if not kicker:
        return ""
    width = min(420, max(172, 40 + len(kicker) * 10))
    x = 70
    y = 70
    return (
        f'<g><rect x="{x}" y="{y}" width="{width}" height="58" rx="29" fill="{fill}" fill-opacity="0.9" />'
        f'<text x="{x + width / 2:.1f}" y="{y + 37}" text-anchor="middle" fill="{text_fill}" '
        'font-family="Manrope, Inter, Arial, sans-serif" font-size="26" font-weight="700" letter-spacing="0.8">'
        f"{_escape(kicker)}</text></g>"
    )


def _footer_block(footer, fill):
    footer = (footer or "").strip()
    if not footer:
        return ""
    return (
        f'<text x="74" y="1032" fill="{fill}" fill-opacity="0.78" '
        'font-family="Manrope, Inter, Arial, sans-serif" font-size="22" font-weight="700" letter-spacing="1.8">'
        f"{_escape(footer).upper()}</text>"
    )


def _common_defs():
    return dedent(
        """
        <filter id="blur-40" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="40" />
        </filter>
        <filter id="blur-72" x="-25%" y="-25%" width="150%" height="150%">
            <feGaussianBlur stdDeviation="72" />
        </filter>
        <filter id="blur-120" x="-35%" y="-35%" width="170%" height="170%">
            <feGaussianBlur stdDeviation="120" />
        </filter>
        <filter id="blur-170" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="170" />
        </filter>
        <filter id="soft-shadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="22" stdDeviation="26" flood-color="#0b1d35" flood-opacity="0.18" />
        </filter>
        """
    )


def _render_aurora_blush():
    return {
        "title_fill": "#182741",
        "title_stroke": "#fdfcff",
        "badge_fill": "#ffffff",
        "badge_text": "#233454",
        "footer_fill": "#233454",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fdf8ff" />
                <stop offset="46%" stop-color="#fff7fc" />
                <stop offset="100%" stop-color="#eff8ff" />
            </linearGradient>
            <radialGradient id="pink-cloud" cx="26%" cy="78%" r="55%">
                <stop offset="0%" stop-color="#ff8bb6" stop-opacity="0.95" />
                <stop offset="55%" stop-color="#ffaccb" stop-opacity="0.58" />
                <stop offset="100%" stop-color="#ffaccb" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="sky-cloud" cx="78%" cy="18%" r="56%">
                <stop offset="0%" stop-color="#a8eeff" stop-opacity="0.95" />
                <stop offset="58%" stop-color="#cdefff" stop-opacity="0.52" />
                <stop offset="100%" stop-color="#cdefff" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="cream-glow" cx="48%" cy="42%" r="58%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9" />
                <stop offset="48%" stop-color="#fff9f7" stop-opacity="0.3" />
                <stop offset="100%" stop-color="#fff9f7" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="white-swoop" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.82" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.08" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="280" cy="880" r="380" fill="url(#pink-cloud)" filter="url(#blur-120)" />
            <circle cx="980" cy="170" r="360" fill="url(#sky-cloud)" filter="url(#blur-120)" />
            <circle cx="560" cy="470" r="350" fill="url(#cream-glow)" filter="url(#blur-170)" />
            <ellipse cx="430" cy="850" rx="470" ry="160" fill="url(#white-swoop)" transform="rotate(-10 430 850)" filter="url(#blur-40)" />
            <path d="M-120 926 C136 710 346 656 580 710 C820 766 1010 734 1320 428 L1320 1180 L-120 1180 Z" fill="url(#white-swoop)" opacity="0.78" filter="url(#blur-72)" />
            <ellipse cx="810" cy="360" rx="400" ry="96" fill="#ffffff" opacity="0.26" transform="rotate(-27 810 360)" filter="url(#blur-72)" />
            """
        ),
    }


def _render_sky_lilac():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#15294c",
        "badge_fill": "#ffffff",
        "badge_text": "#253a66",
        "footer_fill": "#eef5ff",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#d8dfff" />
                <stop offset="50%" stop-color="#b4ddff" />
                <stop offset="100%" stop-color="#a5c9ff" />
            </linearGradient>
            <linearGradient id="beam-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.92" />
                <stop offset="100%" stop-color="#8ee7ff" stop-opacity="0.16" />
            </linearGradient>
            <linearGradient id="beam-b" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#847eff" stop-opacity="0.78" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="panel" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.52" />
                <stop offset="100%" stop-color="#e8f5ff" stop-opacity="0.12" />
            </linearGradient>
            <radialGradient id="glow" cx="28%" cy="28%" r="58%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.72" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <path d="M-120 900 L370 160 L960 620 L470 1360 Z" fill="url(#beam-a)" opacity="0.88" filter="url(#blur-40)" />
            <path d="M120 1030 L560 210 L1110 520 L660 1330 Z" fill="url(#beam-b)" opacity="0.6" filter="url(#blur-72)" />
            <rect x="82" y="-64" width="420" height="1220" rx="80" fill="#ffffff" opacity="0.24" transform="rotate(18 82 -64)" filter="url(#blur-40)" />
            <rect x="790" y="96" width="278" height="216" rx="42" fill="url(#panel)" stroke="#ffffff" stroke-opacity="0.34" />
            <rect x="842" y="148" width="72" height="72" rx="18" fill="#ffffff" fill-opacity="0.52" />
            <rect x="938" y="148" width="88" height="72" rx="18" fill="#cfe9ff" fill-opacity="0.42" />
            <circle cx="258" cy="224" r="280" fill="url(#glow)" filter="url(#blur-120)" />
            """
        ),
    }


def _render_rose_mist():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#511738",
        "badge_fill": "#ffffff",
        "badge_text": "#7b2152",
        "footer_fill": "#fff2f8",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffd6ea" />
                <stop offset="45%" stop-color="#ff9fcb" />
                <stop offset="100%" stop-color="#ffd9ef" />
            </linearGradient>
            <linearGradient id="ribbon-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.32" />
                <stop offset="100%" stop-color="#ff6cab" stop-opacity="0.92" />
            </linearGradient>
            <linearGradient id="ribbon-b" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ff4f95" stop-opacity="0.08" />
                <stop offset="50%" stop-color="#d71b6e" stop-opacity="0.72" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.12" />
            </linearGradient>
            <linearGradient id="ribbon-c" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ff6aa5" stop-opacity="0.12" />
                <stop offset="52%" stop-color="#ffffff" stop-opacity="0.42" />
                <stop offset="100%" stop-color="#ffbad7" stop-opacity="0.82" />
            </linearGradient>
            <radialGradient id="soft-glow" cx="72%" cy="20%" r="42%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.52" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <path d="M-120 780 C154 620 362 588 612 690 C852 786 1028 808 1320 650 L1320 1180 L-120 1180 Z" fill="url(#ribbon-a)" filter="url(#blur-40)" />
            <path d="M-140 540 C132 392 382 370 620 430 C860 490 1032 452 1320 250 L1320 558 C1038 704 816 740 580 694 C348 648 142 676 -140 838 Z" fill="url(#ribbon-b)" filter="url(#blur-72)" />
            <path d="M0 1040 C264 890 408 816 576 822 C754 830 920 910 1200 752 L1200 1100 L0 1100 Z" fill="url(#ribbon-c)" opacity="0.86" filter="url(#blur-40)" />
            <circle cx="930" cy="170" r="240" fill="url(#soft-glow)" filter="url(#blur-120)" />
            <ellipse cx="300" cy="230" rx="320" ry="120" fill="#ffffff" opacity="0.12" transform="rotate(-16 300 230)" filter="url(#blur-72)" />
            """
        ),
    }


def _render_midnight_wave():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#08182f",
        "badge_fill": "#ffffff",
        "badge_text": "#17325d",
        "footer_fill": "#d9e8ff",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#08182f" />
                <stop offset="55%" stop-color="#153b8c" />
                <stop offset="100%" stop-color="#284de6" />
            </linearGradient>
            <linearGradient id="wave-a" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#3ad6ff" stop-opacity="0.12" />
                <stop offset="50%" stop-color="#49b9ff" stop-opacity="0.85" />
                <stop offset="100%" stop-color="#1e4cff" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="wave-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#5ed8ff" stop-opacity="0.04" />
                <stop offset="52%" stop-color="#77b9ff" stop-opacity="0.86" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.22" />
            </linearGradient>
            <radialGradient id="glow" cx="14%" cy="18%" r="48%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9" />
                <stop offset="36%" stop-color="#d5e9ff" stop-opacity="0.42" />
                <stop offset="100%" stop-color="#d5e9ff" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="aura" cx="78%" cy="78%" r="40%">
                <stop offset="0%" stop-color="#1637ff" stop-opacity="0.95" />
                <stop offset="100%" stop-color="#1637ff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="180" cy="130" r="210" fill="url(#glow)" filter="url(#blur-120)" />
            <circle cx="1010" cy="860" r="320" fill="url(#aura)" filter="url(#blur-170)" />
            <path d="M-140 840 C116 710 328 700 560 740 C796 780 1028 768 1320 612 L1320 1180 L-140 1180 Z" fill="url(#wave-a)" filter="url(#blur-40)" />
            <path d="M-120 970 C160 812 388 782 640 812 C894 842 1078 792 1320 640" stroke="url(#wave-b)" stroke-width="176" stroke-linecap="round" fill="none" opacity="0.88" filter="url(#blur-72)" />
            <path d="M-120 560 C160 460 368 482 596 576 C820 668 1030 676 1320 530" stroke="#ffffff" stroke-opacity="0.16" stroke-width="54" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_mint_halo():
    return {
        "title_fill": "#16324c",
        "title_stroke": "#faffff",
        "badge_fill": "#ffffff",
        "badge_text": "#16324c",
        "footer_fill": "#16324c",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#f2fffc" />
                <stop offset="50%" stop-color="#c7fbf2" />
                <stop offset="100%" stop-color="#d7fff5" />
            </linearGradient>
            <radialGradient id="core" cx="72%" cy="34%" r="26%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95" />
                <stop offset="48%" stop-color="#9dffe3" stop-opacity="0.55" />
                <stop offset="100%" stop-color="#9dffe3" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="plane" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.7" />
                <stop offset="100%" stop-color="#91ffe6" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="ring" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#9df6e0" />
                <stop offset="100%" stop-color="#37c8ff" />
            </linearGradient>
            <radialGradient id="lime-blur" cx="18%" cy="82%" r="42%">
                <stop offset="0%" stop-color="#c9ff8d" stop-opacity="0.8" />
                <stop offset="100%" stop-color="#c9ff8d" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="860" cy="320" r="250" fill="url(#core)" filter="url(#blur-72)" />
            <circle cx="180" cy="900" r="280" fill="url(#lime-blur)" filter="url(#blur-120)" />
            <ellipse cx="780" cy="350" rx="234" ry="234" fill="none" stroke="url(#ring)" stroke-width="64" stroke-opacity="0.52" filter="url(#blur-40)" />
            <ellipse cx="780" cy="350" rx="290" ry="290" fill="none" stroke="#ffffff" stroke-width="24" stroke-opacity="0.34" filter="url(#blur-40)" />
            <path d="M-120 948 L650 282 L1360 640 L570 1320 Z" fill="url(#plane)" opacity="0.8" filter="url(#blur-40)" />
            <path d="M164 872 C356 760 592 712 822 726 C924 732 1028 748 1128 770" stroke="#3fd4f5" stroke-opacity="0.46" stroke-width="18" stroke-linecap="round" fill="none" />
            """
        ),
    }


def _render_peach_glow():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#71243b",
        "badge_fill": "#ffffff",
        "badge_text": "#8f3a42",
        "footer_fill": "#fff8f2",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffd7c1" />
                <stop offset="42%" stop-color="#ff8a72" />
                <stop offset="100%" stop-color="#ffb093" />
            </linearGradient>
            <radialGradient id="sun" cx="20%" cy="20%" r="46%">
                <stop offset="0%" stop-color="#fff5dd" stop-opacity="0.98" />
                <stop offset="46%" stop-color="#ffd57d" stop-opacity="0.48" />
                <stop offset="100%" stop-color="#ffd57d" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="fold-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.42" />
                <stop offset="100%" stop-color="#ff5a47" stop-opacity="0.9" />
            </linearGradient>
            <linearGradient id="fold-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ff9257" stop-opacity="0.06" />
                <stop offset="55%" stop-color="#ff4d52" stop-opacity="0.68" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.2" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="210" cy="180" r="290" fill="url(#sun)" filter="url(#blur-120)" />
            <path d="M110 1170 C190 932 304 748 436 590 C578 416 732 294 902 -70" stroke="url(#fold-a)" stroke-width="240" stroke-linecap="round" fill="none" opacity="0.84" filter="url(#blur-40)" />
            <path d="M-120 1040 C120 856 288 712 472 594 C676 462 890 338 1160 62" stroke="url(#fold-b)" stroke-width="174" stroke-linecap="round" fill="none" opacity="0.9" filter="url(#blur-72)" />
            <path d="M0 822 C206 710 382 694 588 728 C802 764 988 736 1200 612" stroke="#ffffff" stroke-opacity="0.22" stroke-width="52" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_violet_satin():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#101e55",
        "badge_fill": "#ffffff",
        "badge_text": "#203c88",
        "footer_fill": "#e8edff",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#4e52ff" />
                <stop offset="50%" stop-color="#7c6bff" />
                <stop offset="100%" stop-color="#d3d8ff" />
            </linearGradient>
            <linearGradient id="fold-1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.76" />
                <stop offset="100%" stop-color="#6372ff" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="fold-2" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#4d59ff" stop-opacity="0.08" />
                <stop offset="52%" stop-color="#192ccf" stop-opacity="0.7" />
                <stop offset="100%" stop-color="#eff2ff" stop-opacity="0.8" />
            </linearGradient>
            <linearGradient id="fold-3" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#eef2ff" stop-opacity="0.72" />
                <stop offset="100%" stop-color="#7b8dff" stop-opacity="0.16" />
            </linearGradient>
            <radialGradient id="halo" cx="24%" cy="18%" r="38%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.74" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="240" cy="180" r="260" fill="url(#halo)" filter="url(#blur-120)" />
            <path d="M120 1180 C110 948 146 742 264 526 C360 350 432 186 418 -80" stroke="url(#fold-1)" stroke-width="290" stroke-linecap="round" fill="none" opacity="0.96" filter="url(#blur-40)" />
            <path d="M532 1190 C510 986 556 792 704 550 C818 364 910 204 892 -70" stroke="url(#fold-2)" stroke-width="320" stroke-linecap="round" fill="none" opacity="0.92" filter="url(#blur-40)" />
            <path d="M936 1180 C930 964 978 760 1100 520 C1170 386 1220 246 1228 -54" stroke="url(#fold-3)" stroke-width="266" stroke-linecap="round" fill="none" opacity="0.9" filter="url(#blur-40)" />
            <path d="M92 792 C330 654 586 624 824 666 C996 696 1120 686 1230 642" stroke="#ffffff" stroke-opacity="0.14" stroke-width="38" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_golden_haze():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#124d74",
        "badge_fill": "#ffffff",
        "badge_text": "#124d74",
        "footer_fill": "#f2ffff",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#00b2e8" />
                <stop offset="58%" stop-color="#49d7ff" />
                <stop offset="100%" stop-color="#a9f06d" />
            </linearGradient>
            <radialGradient id="sun-a" cx="72%" cy="90%" r="44%">
                <stop offset="0%" stop-color="#d8ff93" stop-opacity="0.95" />
                <stop offset="60%" stop-color="#d8ff93" stop-opacity="0.32" />
                <stop offset="100%" stop-color="#d8ff93" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="sun-b" cx="18%" cy="18%" r="34%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.86" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="veil-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.38" />
                <stop offset="100%" stop-color="#32b2ff" stop-opacity="0.02" />
            </linearGradient>
            <linearGradient id="veil-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#0a7dff" stop-opacity="0.12" />
                <stop offset="60%" stop-color="#ffffff" stop-opacity="0.3" />
                <stop offset="100%" stop-color="#b0ff8f" stop-opacity="0.18" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="964" cy="960" r="350" fill="url(#sun-a)" filter="url(#blur-120)" />
            <circle cx="220" cy="180" r="210" fill="url(#sun-b)" filter="url(#blur-120)" />
            <path d="M-140 1040 L248 120 C418 260 564 382 772 516 C944 626 1070 676 1320 722 L1320 1220 L-140 1220 Z" fill="url(#veil-a)" filter="url(#blur-40)" />
            <path d="M-120 882 C132 716 360 634 600 642 C838 650 1036 742 1320 566" fill="none" stroke="url(#veil-b)" stroke-width="210" stroke-linecap="round" opacity="0.76" filter="url(#blur-72)" />
            <path d="M0 460 C214 298 442 270 650 344 C834 408 1008 510 1200 432" stroke="#ffffff" stroke-opacity="0.18" stroke-width="56" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_brand_horizon():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#16324c",
        "badge_fill": "#ffffff",
        "badge_text": "#1c3551",
        "footer_fill": "#eef6ff",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0a76cb" />
                <stop offset="58%" stop-color="#0a76cb" />
                <stop offset="100%" stop-color="#b8860b" />
            </linearGradient>
            <radialGradient id="top-glow" cx="22%" cy="18%" r="42%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.56" />
                <stop offset="48%" stop-color="#d7ecff" stop-opacity="0.18" />
                <stop offset="100%" stop-color="#d7ecff" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="gold-glow" cx="90%" cy="88%" r="36%">
                <stop offset="0%" stop-color="#ffd98a" stop-opacity="0.86" />
                <stop offset="58%" stop-color="#ffd98a" stop-opacity="0.28" />
                <stop offset="100%" stop-color="#ffd98a" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="veil-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.34" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.02" />
            </linearGradient>
            <linearGradient id="veil-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#0f5ca8" stop-opacity="0.12" />
                <stop offset="55%" stop-color="#ffffff" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#ffd98a" stop-opacity="0.16" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="230" cy="170" r="250" fill="url(#top-glow)" filter="url(#blur-120)" />
            <circle cx="1040" cy="930" r="280" fill="url(#gold-glow)" filter="url(#blur-120)" />
            <path d="M-140 1036 L280 130 C448 262 610 392 820 532 C976 636 1102 702 1320 774 L1320 1220 L-140 1220 Z" fill="url(#veil-a)" opacity="0.82" filter="url(#blur-40)" />
            <path d="M-110 812 C144 664 380 620 626 648 C852 674 1046 774 1320 616" fill="none" stroke="url(#veil-b)" stroke-width="198" stroke-linecap="round" opacity="0.84" filter="url(#blur-72)" />
            <path d="M-40 450 C180 326 406 300 612 360 C792 414 974 510 1210 448" stroke="#ffffff" stroke-opacity="0.18" stroke-width="52" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            <path d="M88 930 C310 830 544 820 786 858 C950 884 1070 868 1206 810" stroke="#f8df9f" stroke-opacity="0.18" stroke-width="34" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_bronze_nocturne():
    return {
        "title_fill": "#fff7eb",
        "title_stroke": "#1a2436",
        "badge_fill": "#fff7eb",
        "badge_text": "#3c2a13",
        "footer_fill": "#f6ead5",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#081524" />
                <stop offset="54%" stop-color="#102a47" />
                <stop offset="100%" stop-color="#8c5b13" />
            </linearGradient>
            <radialGradient id="bronze-core" cx="88%" cy="82%" r="42%">
                <stop offset="0%" stop-color="#ffc96a" stop-opacity="0.92" />
                <stop offset="58%" stop-color="#ffc96a" stop-opacity="0.26" />
                <stop offset="100%" stop-color="#ffc96a" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="navy-glow" cx="20%" cy="16%" r="38%">
                <stop offset="0%" stop-color="#d9edff" stop-opacity="0.56" />
                <stop offset="100%" stop-color="#d9edff" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="arc-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fff1cf" stop-opacity="0.58" />
                <stop offset="100%" stop-color="#ffb84d" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="arc-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#4c8bff" stop-opacity="0.08" />
                <stop offset="56%" stop-color="#ffffff" stop-opacity="0.24" />
                <stop offset="100%" stop-color="#f5c067" stop-opacity="0.22" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="1030" cy="900" r="300" fill="url(#bronze-core)" filter="url(#blur-120)" />
            <circle cx="220" cy="150" r="230" fill="url(#navy-glow)" filter="url(#blur-120)" />
            <path d="M-80 968 C150 756 362 670 598 678 C820 686 1042 762 1310 560" fill="none" stroke="url(#arc-a)" stroke-width="198" stroke-linecap="round" opacity="0.82" filter="url(#blur-72)" />
            <path d="M-110 730 C118 558 338 510 562 534 C790 560 998 646 1260 458" fill="none" stroke="url(#arc-b)" stroke-width="110" stroke-linecap="round" opacity="0.7" filter="url(#blur-40)" />
            <ellipse cx="880" cy="260" rx="330" ry="86" fill="#ffffff" opacity="0.12" transform="rotate(-20 880 260)" filter="url(#blur-72)" />
            """
        ),
    }


def _render_emerald_glass():
    return {
        "title_fill": "#ffffff",
        "title_stroke": "#0b2f2b",
        "badge_fill": "#ffffff",
        "badge_text": "#11413a",
        "footer_fill": "#ecfffb",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0e6e68" />
                <stop offset="52%" stop-color="#22b8a8" />
                <stop offset="100%" stop-color="#97f3c7" />
            </linearGradient>
            <linearGradient id="glass" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.54" />
                <stop offset="100%" stop-color="#d8fff5" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="beam" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#0d7268" stop-opacity="0.08" />
                <stop offset="55%" stop-color="#ffffff" stop-opacity="0.2" />
                <stop offset="100%" stop-color="#d1ff92" stop-opacity="0.24" />
            </linearGradient>
            <radialGradient id="mint-core" cx="18%" cy="18%" r="38%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.72" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="210" cy="160" r="240" fill="url(#mint-core)" filter="url(#blur-120)" />
            <rect x="126" y="116" width="340" height="252" rx="46" fill="url(#glass)" stroke="#ffffff" stroke-opacity="0.32" />
            <rect x="744" y="172" width="284" height="214" rx="40" fill="url(#glass)" stroke="#ffffff" stroke-opacity="0.22" />
            <rect x="572" y="540" width="444" height="286" rx="52" fill="url(#glass)" stroke="#ffffff" stroke-opacity="0.22" />
            <path d="M-120 996 L314 136 C540 292 728 430 932 626 C1036 726 1126 810 1320 920 L1320 1220 L-120 1220 Z" fill="url(#beam)" opacity="0.84" filter="url(#blur-40)" />
            <path d="M0 742 C236 640 470 632 716 684 C904 722 1050 726 1200 678" stroke="#ffffff" stroke-opacity="0.16" stroke-width="42" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_paper_sunrise():
    return {
        "title_fill": "#1a2c45",
        "title_stroke": "#fffaf4",
        "badge_fill": "#ffffff",
        "badge_text": "#374a63",
        "footer_fill": "#374a63",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fff8ef" />
                <stop offset="54%" stop-color="#ffe6d2" />
                <stop offset="100%" stop-color="#ffd19d" />
            </linearGradient>
            <radialGradient id="sun" cx="20%" cy="22%" r="36%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95" />
                <stop offset="48%" stop-color="#ffe9bb" stop-opacity="0.42" />
                <stop offset="100%" stop-color="#ffe9bb" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="sheet-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.78" />
                <stop offset="100%" stop-color="#fff4e6" stop-opacity="0.12" />
            </linearGradient>
            <linearGradient id="sheet-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ffc88f" stop-opacity="0.12" />
                <stop offset="50%" stop-color="#ffffff" stop-opacity="0.38" />
                <stop offset="100%" stop-color="#ffb784" stop-opacity="0.18" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="220" cy="180" r="240" fill="url(#sun)" filter="url(#blur-120)" />
            <rect x="-30" y="556" width="760" height="360" rx="76" fill="url(#sheet-a)" transform="rotate(-9 -30 556)" filter="url(#blur-40)" />
            <rect x="420" y="180" width="840" height="350" rx="82" fill="url(#sheet-b)" transform="rotate(9 420 180)" filter="url(#blur-40)" />
            <ellipse cx="808" cy="772" rx="430" ry="124" fill="#ffffff" opacity="0.14" transform="rotate(-14 808 772)" filter="url(#blur-72)" />
            <path d="M-80 830 C182 688 418 666 668 718 C888 762 1046 744 1250 634" stroke="#ffcb8c" stroke-opacity="0.2" stroke-width="46" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_crimson_silk():
    return {
        "title_fill": "#fff6fb",
        "title_stroke": "#4f1235",
        "badge_fill": "#ffffff",
        "badge_text": "#6f1748",
        "footer_fill": "#fff1f8",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffc3d8" />
                <stop offset="46%" stop-color="#df3d74" />
                <stop offset="100%" stop-color="#7d1238" />
            </linearGradient>
            <linearGradient id="silk-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.42" />
                <stop offset="100%" stop-color="#ff7aa6" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="silk-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ff8db6" stop-opacity="0.08" />
                <stop offset="50%" stop-color="#b40f4f" stop-opacity="0.72" />
                <stop offset="100%" stop-color="#fff0f7" stop-opacity="0.36" />
            </linearGradient>
            <radialGradient id="rose-flare" cx="18%" cy="18%" r="34%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.74" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="214" cy="174" r="220" fill="url(#rose-flare)" filter="url(#blur-120)" />
            <path d="M80 1170 C150 924 284 726 450 536 C622 336 790 176 900 -66" stroke="url(#silk-a)" stroke-width="256" stroke-linecap="round" fill="none" opacity="0.9" filter="url(#blur-40)" />
            <path d="M-100 1028 C162 858 344 698 520 516 C704 326 886 168 1140 -70" stroke="url(#silk-b)" stroke-width="182" stroke-linecap="round" fill="none" opacity="0.9" filter="url(#blur-72)" />
            <path d="M10 802 C236 712 430 714 652 766 C860 814 1048 792 1226 692" stroke="#ffffff" stroke-opacity="0.16" stroke-width="40" stroke-linecap="round" fill="none" filter="url(#blur-40)" />
            """
        ),
    }


def _render_ice_circuit():
    return {
        "title_fill": "#183456",
        "title_stroke": "#ffffff",
        "badge_fill": "#ffffff",
        "badge_text": "#21456d",
        "footer_fill": "#21456d",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#eef7ff" />
                <stop offset="52%" stop-color="#cde9ff" />
                <stop offset="100%" stop-color="#97d4ff" />
            </linearGradient>
            <linearGradient id="beam-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.88" />
                <stop offset="100%" stop-color="#c8ebff" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="beam-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#88d0ff" stop-opacity="0.08" />
                <stop offset="56%" stop-color="#1f7eff" stop-opacity="0.34" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0.24" />
            </linearGradient>
            <radialGradient id="ice-core" cx="18%" cy="18%" r="36%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.84" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="210" cy="170" r="230" fill="url(#ice-core)" filter="url(#blur-120)" />
            <path d="M-140 950 L320 130 L940 500 L470 1310 Z" fill="url(#beam-a)" opacity="0.84" filter="url(#blur-40)" />
            <path d="M82 1048 L562 164 L1120 520 L642 1370 Z" fill="url(#beam-b)" opacity="0.64" filter="url(#blur-72)" />
            <path d="M154 218 H438 M438 218 V362 M438 362 H642 M642 362 V520 M642 520 H920" stroke="#ffffff" stroke-opacity="0.46" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" />
            <circle cx="438" cy="218" r="18" fill="#ffffff" fill-opacity="0.72" />
            <circle cx="642" cy="362" r="18" fill="#78baff" fill-opacity="0.88" />
            <circle cx="920" cy="520" r="18" fill="#ffffff" fill-opacity="0.72" />
            """
        ),
    }


def _render_noir_orchid():
    return {
        "title_fill": "#f8f4ff",
        "title_stroke": "#131426",
        "badge_fill": "#ffffff",
        "badge_text": "#2e2b5c",
        "footer_fill": "#eae6ff",
        "defs": dedent(
            """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0d1018" />
                <stop offset="56%" stop-color="#23294e" />
                <stop offset="100%" stop-color="#7f45ff" />
            </linearGradient>
            <radialGradient id="orchid-glow" cx="82%" cy="24%" r="34%">
                <stop offset="0%" stop-color="#dcb4ff" stop-opacity="0.9" />
                <stop offset="58%" stop-color="#dcb4ff" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#dcb4ff" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="white-halo" cx="20%" cy="18%" r="30%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.64" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="wave-a" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.34" />
                <stop offset="100%" stop-color="#b999ff" stop-opacity="0.06" />
            </linearGradient>
            <linearGradient id="wave-b" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#6c45ff" stop-opacity="0.08" />
                <stop offset="50%" stop-color="#4424d6" stop-opacity="0.72" />
                <stop offset="100%" stop-color="#f4ecff" stop-opacity="0.3" />
            </linearGradient>
            """
        ),
        "body": dedent(
            """
            <rect width="1200" height="1100" fill="url(#bg)" />
            <circle cx="970" cy="220" r="240" fill="url(#orchid-glow)" filter="url(#blur-120)" />
            <circle cx="210" cy="170" r="210" fill="url(#white-halo)" filter="url(#blur-120)" />
            <path d="M-120 878 C132 706 364 648 608 684 C844 718 1030 802 1320 612" fill="none" stroke="url(#wave-a)" stroke-width="204" stroke-linecap="round" opacity="0.86" filter="url(#blur-72)" />
            <path d="M-110 666 C122 524 340 492 560 524 C800 556 1012 648 1300 472" fill="none" stroke="url(#wave-b)" stroke-width="122" stroke-linecap="round" opacity="0.74" filter="url(#blur-40)" />
            <ellipse cx="742" cy="790" rx="380" ry="100" fill="#ffffff" opacity="0.08" transform="rotate(-18 742 790)" filter="url(#blur-72)" />
            """
        ),
    }


RENDERERS = {
    "aurora_blush": _render_aurora_blush,
    "sky_lilac": _render_sky_lilac,
    "rose_mist": _render_rose_mist,
    "midnight_wave": _render_midnight_wave,
    "mint_halo": _render_mint_halo,
    "peach_glow": _render_peach_glow,
    "violet_satin": _render_violet_satin,
    "golden_haze": _render_golden_haze,
    "brand_horizon": _render_brand_horizon,
    "bronze_nocturne": _render_bronze_nocturne,
    "emerald_glass": _render_emerald_glass,
    "paper_sunrise": _render_paper_sunrise,
    "crimson_silk": _render_crimson_silk,
    "ice_circuit": _render_ice_circuit,
    "noir_orchid": _render_noir_orchid,
}


def build_cover_svg(title, preset_key="aurora_blush", kicker="", footer="AzureLMS Course"):
    preset = GRADIENT_PRESET_MAP.get(preset_key, GRADIENT_PRESET_MAP["aurora_blush"])
    artwork = RENDERERS.get(preset["renderer"], _render_aurora_blush)()

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" fill="none">
        <defs>
            {_common_defs()}
            {artwork["defs"]}
        </defs>
        <g filter="url(#soft-shadow)">
            {artwork["body"]}
        </g>
        {_badge_block(kicker, artwork["badge_fill"], artwork["badge_text"])}
        {_title_block(title, artwork["title_fill"], artwork["title_stroke"])}
        {_footer_block(footer, artwork["footer_fill"])}
    </svg>
    """
    return dedent(svg).strip()


def build_cover_data_uri(title, preset_key="aurora_blush", kicker="", footer="AzureLMS Course"):
    svg = build_cover_svg(title=title, preset_key=preset_key, kicker=kicker, footer=footer)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
