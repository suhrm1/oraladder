import os
from PIL import Image, ImageDraw, ImageFont

OVERLAY_SIZE = 90


def _find_font():
    candidates = [
        "/usr/share/fonts/noto/NotoSansMono-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/TTF/NotoSansMNerdFontMono-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/Adwaita/AdwaitaMono-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise RuntimeError("No suitable font found. Install a bold monospace font " "(e.g. fonts-noto, fonts-dejavu-core).")


def generate_overlay(season, verbose=False):
    font_path = _find_font()
    title_font = ImageFont.truetype(font_path, 18)
    season_font = ImageFont.truetype(font_path, 14)

    img = Image.new("RGBA", (OVERLAY_SIZE, OVERLAY_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def draw_text(text, font, y_pos):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (OVERLAY_SIZE - tw) // 2
        offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1), (0, -1), (0, 1), (-1, 0), (1, 0)]
        for ox, oy in offsets:
            draw.text((x + ox, y_pos + oy), text, font=font, fill="black")
        draw.text((x, y_pos), text, font=font, fill="white")

    draw_text("Ladder", title_font, 2)
    draw_text(season, season_font, OVERLAY_SIZE - 20)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(out_dir, "..", "overlay.svg")
    png_path = os.path.join(out_dir, "..", "overlay.png")

    _generate_svg(svg_path, season)

    img.save(png_path)
    if verbose:
        print(f"  Overlay PNG: {png_path}")
        print(f"  Overlay SVG: {svg_path}")

    return svg_path, png_path


def _generate_svg(svg_path, season):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="90" height="90" viewBox="0 0 90 90">
  <defs>
    <style>
      .t {{ font-family: monospace; font-weight: bold; fill: white; }}
      .o {{ stroke: black; stroke-width: 2; stroke-linejoin: round; paint-order: stroke; }}
    </style>
  </defs>
  <text x="45" y="16" text-anchor="middle" class="t o" font-size="18">Ladder</text>
  <text x="45" y="76" text-anchor="middle" class="t o" font-size="14">{season}</text>
</svg>"""
    with open(svg_path, "w") as f:
        f.write(svg)
