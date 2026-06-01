"""Generate icon.png (512×512) and presplash.jpg (1080×1920) using Pillow.

Run once before building the APK:
    python create_assets.py

Requirements: pillow (pip install pillow)
"""
import math
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit('Pillow is required: pip install pillow')

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)


def _gradient_bg(draw: ImageDraw.ImageDraw, width: int, height: int,
                 top: tuple, bottom: tuple):
    for y in range(height):
        t = y / height
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def make_icon():
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Gradient background circle
    for y in range(size):
        t = y / size
        r = int(79 * (1 - t) + 2 * t)
        g = int(195 * (1 - t) + 119 * t)
        b = int(247 * (1 - t) + 189 * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Clip to circle
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)

    # Sun circle
    cx, cy = size // 2, size // 2 - 20
    sun_r = 90
    draw.ellipse(
        [cx - sun_r, cy - sun_r, cx + sun_r, cy + sun_r],
        fill=(255, 220, 50, 240),
    )

    # Sun rays
    for i in range(8):
        angle = math.radians(i * 45)
        inner = sun_r + 10
        outer = sun_r + 55
        x1 = cx + math.cos(angle) * inner
        y1 = cy + math.sin(angle) * inner
        x2 = cx + math.cos(angle) * outer
        y2 = cy + math.sin(angle) * outer
        draw.line([x1, y1, x2, y2], fill=(255, 240, 120, 200), width=12)

    # Cloud shape
    cloud_cx, cloud_cy = cx + 30, cy + 75
    draw.ellipse([cloud_cx - 40, cloud_cy - 30, cloud_cx + 40, cloud_cy + 30], fill=(240, 248, 255, 230))
    draw.ellipse([cloud_cx - 20, cloud_cy - 50, cloud_cx + 60, cloud_cy + 10], fill=(240, 248, 255, 230))
    draw.ellipse([cloud_cx - 75, cloud_cy - 25, cloud_cx + 5, cloud_cy + 20], fill=(240, 248, 255, 230))

    path = os.path.join(ASSETS_DIR, 'icon.png')
    img.save(path, 'PNG')
    print(f'Created {path}')


def make_presplash():
    width, height = 1080, 1920
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    _gradient_bg(draw, width, height, (13, 90, 153), (4, 30, 66))

    # Sun
    cx, cy = width // 2, height // 2 - 140
    sun_r = 140
    draw.ellipse([cx - sun_r, cy - sun_r, cx + sun_r, cy + sun_r], fill=(250, 210, 60))

    # Rays
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = cx + math.cos(angle) * (sun_r + 16)
        y1 = cy + math.sin(angle) * (sun_r + 16)
        x2 = cx + math.cos(angle) * (sun_r + 90)
        y2 = cy + math.sin(angle) * (sun_r + 90)
        draw.line([x1, y1, x2, y2], fill=(255, 235, 120, 200), width=18)

    # App name
    try:
        font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 120)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 48)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = font_large

    # "Weather" title
    text = 'Weather'
    bbox = draw.textbbox((0, 0), text, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, cy + 220), text, font=font_large, fill=(255, 255, 255, 230))

    # Subtitle
    sub = 'Your sky. Always.'
    bbox2 = draw.textbbox((0, 0), sub, font=font_small)
    sw = bbox2[2] - bbox2[0]
    draw.text(((width - sw) // 2, cy + 360), sub, font=font_small, fill=(200, 220, 240, 180))

    path = os.path.join(ASSETS_DIR, 'presplash.jpg')
    img.save(path, 'JPEG', quality=92)
    print(f'Created {path}')


if __name__ == '__main__':
    make_icon()
    make_presplash()
    print('Assets generated successfully.')
