"""Generate assets/icon.png (512×512) and assets/presplash.jpg (1080×1920).

Run once before building the APK:
    python3 create_assets.py

After changing presplash, bust the p4a cache before rebuilding:
    find ~/.weatherapp-build -name "presplash*" -exec rm -f {} \\;

Requirements: pillow  (pip install pillow)
Notes from ANDROID_APP_PLAYBOOK.md:
  - icon must be PNG (buildozer scales it)
  - presplash MUST be JPG — p4a silently ignores .png presplash
"""
import math
import os

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    raise SystemExit('Pillow is required: pip install pillow')

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)


# ─── colour helpers ────────────────────────────────────────────────────────────

def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_color(y_frac, stops):
    """stops = list of (frac, (r,g,b)) sorted by frac."""
    for i in range(len(stops) - 1):
        f0, c0 = stops[i]
        f1, c1 = stops[i + 1]
        if y_frac <= f1:
            t = (y_frac - f0) / max(f1 - f0, 1e-6)
            return _lerp_color(c0, c1, max(0.0, min(1.0, t)))
    return stops[-1][1]


# ─── presplash ─────────────────────────────────────────────────────────────────

def make_presplash():
    W, H = 1080, 1920

    # ── sky gradient (scanline) ───────────────────────────────────────────────
    sky = Image.new('RGB', (W, H))
    sky_draw = ImageDraw.Draw(sky)

    # colour stops: deep midnight blue at top → cerulean → pale gold at horizon
    sky_stops = [
        (0.00, (8,  48, 118)),
        (0.28, (18, 86, 188)),
        (0.56, (52, 142, 225)),
        (0.76, (120, 195, 238)),
        (0.90, (172, 220, 245)),
        (1.00, (205, 233, 250)),
    ]

    HORIZON_Y = 1340   # mountains sit here
    SUN_CX, SUN_CY = W // 2, 730   # sun a bit above centre

    for y in range(H):
        frac = y / HORIZON_Y if y < HORIZON_Y else 1.0
        r, g, b = _gradient_color(min(frac, 1.0), sky_stops)

        # warm golden-amber glow radiating from sun position
        dy = abs(y - SUN_CY)
        glow_t = max(0.0, 1.0 - dy / 700) ** 2.0
        r = min(255, r + int(72 * glow_t))
        g = min(255, g + int(46 * glow_t))
        b = max(0,   b - int(28 * glow_t))

        sky_draw.line([(0, y), (W, y)], fill=(r, g, b))

    img = sky.convert('RGBA')

    # ── sun halo (blurred glow layers) ────────────────────────────────────────
    for radius, alpha in [(520, 18), (380, 32), (280, 52), (200, 85), (148, 130)]:
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse(
            [SUN_CX - radius, SUN_CY - radius, SUN_CX + radius, SUN_CY + radius],
            fill=(255, 225, 90, alpha),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=radius // 5))
        img = Image.alpha_composite(img, glow)

    # ── sun rays (16 thin triangles) ──────────────────────────────────────────
    RAY_INNER = 148        # starts just outside core
    RAY_OUTER = 460        # how far rays extend
    RAY_WIDTH = 6          # tip half-width in degrees

    ray_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ray_draw = ImageDraw.Draw(ray_layer)

    for i in range(16):
        angle = math.radians(i * (360 / 16) - 90)
        angle_left  = angle - math.radians(RAY_WIDTH)
        angle_right = angle + math.radians(RAY_WIDTH)

        # base (inner circle edge) — two points slightly apart
        bx1 = SUN_CX + math.cos(angle_left)  * RAY_INNER
        by1 = SUN_CY + math.sin(angle_left)  * RAY_INNER
        bx2 = SUN_CX + math.cos(angle_right) * RAY_INNER
        by2 = SUN_CY + math.sin(angle_right) * RAY_INNER
        # tip
        tx  = SUN_CX + math.cos(angle) * RAY_OUTER
        ty  = SUN_CY + math.sin(angle) * RAY_OUTER

        ray_draw.polygon([(bx1, by1), (bx2, by2), (tx, ty)],
                         fill=(255, 238, 140, 110))

    ray_layer = ray_layer.filter(ImageFilter.GaussianBlur(radius=6))
    img = Image.alpha_composite(img, ray_layer)

    # ── sun core ──────────────────────────────────────────────────────────────
    sun_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sun_draw = ImageDraw.Draw(sun_layer)
    SUN_R = 142

    # outer limb glow
    sun_draw.ellipse(
        [SUN_CX - SUN_R - 22, SUN_CY - SUN_R - 22,
         SUN_CX + SUN_R + 22, SUN_CY + SUN_R + 22],
        fill=(255, 235, 100, 180),
    )
    # main disc
    sun_draw.ellipse(
        [SUN_CX - SUN_R, SUN_CY - SUN_R, SUN_CX + SUN_R, SUN_CY + SUN_R],
        fill=(255, 248, 180, 255),
    )
    # bright centre
    sun_draw.ellipse(
        [SUN_CX - SUN_R // 2, SUN_CY - SUN_R // 2,
         SUN_CX + SUN_R // 2, SUN_CY + SUN_R // 2],
        fill=(255, 255, 230, 255),
    )
    img = Image.alpha_composite(img, sun_layer)

    # ── clouds ────────────────────────────────────────────────────────────────
    def draw_cloud(layer, cx, cy, sc, alpha=220):
        ld = ImageDraw.Draw(layer)
        def puff(x, y, rx, ry):
            ld.ellipse([cx + x - rx*sc, cy + y - ry*sc,
                        cx + x + rx*sc, cy + y + ry*sc],
                       fill=(245, 252, 255, alpha))
        # bottom base rectangle
        ld.rectangle([cx - 110*sc, cy - 18*sc, cx + 110*sc, cy + 22*sc],
                     fill=(245, 252, 255, alpha))
        # puffs
        puff(-72, -22, 42, 38)
        puff(-30, -38, 52, 48)
        puff( 20, -46, 58, 52)
        puff( 74, -28, 46, 40)
        puff( 108, -10, 32, 28)

    # Cloud 1 — upper left, medium
    cl1 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_cloud(cl1, cx=260, cy=410, sc=1.05, alpha=210)
    cl1 = cl1.filter(ImageFilter.GaussianBlur(radius=3))
    img = Image.alpha_composite(img, cl1)

    # Cloud 2 — upper right, slightly smaller
    cl2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_cloud(cl2, cx=820, cy=310, sc=0.85, alpha=195)
    cl2 = cl2.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(img, cl2)

    # ── mountain silhouettes ──────────────────────────────────────────────────
    img = img.convert('RGB')
    mtn_draw = ImageDraw.Draw(img)

    def mountain_range(peaks, base_y, color):
        """peaks = list of (cx, peak_y, half_width)."""
        poly = [(0, base_y)]
        for i, (cx, peak_y, hw) in enumerate(peaks):
            poly.append((cx - hw, base_y))
            poly.append((cx, peak_y))
            poly.append((cx + hw, base_y))
        poly.append((W, base_y))
        poly.append((W, H))
        poly.append((0, H))
        mtn_draw.polygon(poly, fill=color)

    # Far range (lightest, most distant)
    far_peaks = [
        (120, HORIZON_Y - 210, 200),
        (310, HORIZON_Y - 295, 180),
        (520, HORIZON_Y - 240, 220),
        (720, HORIZON_Y - 310, 195),
        (880, HORIZON_Y - 255, 210),
        (1040, HORIZON_Y - 180, 165),
    ]
    mountain_range(far_peaks, HORIZON_Y, (58, 82, 140))

    # Mid range
    mid_peaks = [
        (-30, HORIZON_Y - 160, 190),
        (185, HORIZON_Y - 245, 200),
        (420, HORIZON_Y - 285, 210),
        (640, HORIZON_Y - 230, 185),
        (830, HORIZON_Y - 270, 200),
        (1050, HORIZON_Y - 155, 175),
        (1150, HORIZON_Y - 120, 160),
    ]
    mountain_range(mid_peaks, HORIZON_Y + 60, (38, 52, 105))

    # Near range (darkest)
    near_peaks = [
        (-50,  HORIZON_Y + 10, 220),
        (180,  HORIZON_Y - 115, 230),
        (440,  HORIZON_Y - 140, 240),
        (680,  HORIZON_Y - 100, 210),
        (870,  HORIZON_Y - 135, 225),
        (1080, HORIZON_Y - 80,  200),
        (1200, HORIZON_Y + 20, 190),
    ]
    mountain_range(near_peaks, HORIZON_Y + 120, (22, 30, 72))

    # Snow caps on the tallest visible peaks
    snow_color = (225, 238, 252)
    for cx, py, hw in far_peaks:
        cap_h = int(hw * 0.22)
        cap_w = int(hw * 0.28)
        mtn_draw.polygon([
            (cx - cap_w, py + cap_h + 8),
            (cx, py),
            (cx + cap_w, py + cap_h + 8),
        ], fill=snow_color)

    # ── ground / base fill (below near mountains) ─────────────────────────────
    mtn_draw.rectangle([0, HORIZON_Y + 180, W, H], fill=(14, 20, 52))

    # ── horizon atmospheric haze ──────────────────────────────────────────────
    img_rgba = img.convert('RGBA')
    haze = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    haze_draw = ImageDraw.Draw(haze)
    for hy in range(HORIZON_Y - 80, HORIZON_Y + 60):
        t = max(0.0, 1.0 - abs(hy - HORIZON_Y) / 80.0)
        haze_draw.line([(0, hy), (W, hy)], fill=(200, 230, 255, int(38 * t)))
    img = Image.alpha_composite(img_rgba, haze).convert('RGB')

    # ── text ──────────────────────────────────────────────────────────────────
    draw = ImageDraw.Draw(img)

    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf',
    ]
    font_paths_reg = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
    ]

    def load_font(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
        return ImageFont.load_default()

    font_main = load_font(font_paths, 90)
    font_sub  = load_font(font_paths_reg, 52)

    def draw_text_centered(text, font, y, color, shadow_color=(0, 0, 0, 140)):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        # drop shadow
        draw.text((x + 3, y + 3), text, font=font, fill=shadow_color)
        draw.text((x, y), text, font=font, fill=color)

    draw_text_centered('Loading', font_main, y=1680, color=(255, 255, 255))
    draw_text_centered('(a perfect day)...', font_sub, y=1790, color=(200, 230, 255))

    path = os.path.join(ASSETS_DIR, 'presplash.jpg')
    img.save(path, 'JPEG', quality=96)
    print(f'Created {path}')


# ─── app icon ──────────────────────────────────────────────────────────────────

def make_icon():
    SIZE = 512
    MARGIN = 30     # breathing room inside the square

    # ── background: rounded square, deep-blue gradient ────────────────────────
    bg = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)

    # scanline gradient: deep navy top → cerulean blue bottom
    for y in range(SIZE):
        t = y / SIZE
        r = int(8  + (28  - 8)  * t)
        g = int(48 + (110 - 48) * t)
        b = int(118+ (210 - 118)* t)
        bg_draw.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))

    # clip to rounded square
    mask = Image.new('L', (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    CORNER = 90
    mask_draw.rounded_rectangle([0, 0, SIZE, SIZE], radius=CORNER, fill=255)
    bg.putalpha(mask)

    img = bg.convert('RGBA')

    # ── sun halo ───────────────────────────────────────────────────────────────
    CX = SIZE // 2
    CY = SIZE // 2 + 8   # very slightly below centre feels more grounded

    for r, a in [(230, 20), (190, 38), (155, 62), (125, 95), (100, 138)]:
        glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([CX-r, CY-r, CX+r, CY+r], fill=(255, 225, 80, a))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=r // 6))
        img = Image.alpha_composite(img, glow)

    # ── sun rays ───────────────────────────────────────────────────────────────
    N_RAYS   = 12
    R_INNER  = 90
    R_OUTER  = 215
    RAY_DEG  = 7    # half-angle of each ray tip

    rays = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)

    for i in range(N_RAYS):
        angle = math.radians(i * (360 / N_RAYS) - 90)
        al    = angle - math.radians(RAY_DEG)
        ar    = angle + math.radians(RAY_DEG)
        bx1 = CX + math.cos(al) * R_INNER
        by1 = CY + math.sin(al) * R_INNER
        bx2 = CX + math.cos(ar) * R_INNER
        by2 = CY + math.sin(ar) * R_INNER
        tx  = CX + math.cos(angle) * R_OUTER
        ty  = CY + math.sin(angle) * R_OUTER
        rd.polygon([(bx1, by1), (bx2, by2), (tx, ty)],
                   fill=(255, 238, 120, 170))

    rays = rays.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, rays)

    # ── sun disc ───────────────────────────────────────────────────────────────
    sun_layer = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun_layer)
    R = 88

    # outer glow ring
    sd.ellipse([CX-R-16, CY-R-16, CX+R+16, CY+R+16], fill=(255, 230, 90, 200))
    # main disc
    sd.ellipse([CX-R, CY-R, CX+R, CY+R], fill=(255, 245, 160, 255))
    # bright core
    Rc = R // 2
    sd.ellipse([CX-Rc, CY-Rc, CX+Rc, CY+Rc], fill=(255, 255, 225, 255))

    img = Image.alpha_composite(img, sun_layer)

    # ── composite onto white backing and re-mask ───────────────────────────────
    final = Image.new('RGBA', (SIZE, SIZE), (255, 255, 255, 0))
    final = Image.alpha_composite(final, img)

    # re-apply rounded corner mask so edges are clean
    final.putalpha(mask)

    path = os.path.join(ASSETS_DIR, 'icon.png')
    final.save(path, 'PNG')
    print(f'Created {path}')


# ─── main ──────────────────────────────────────────────────────────────────────

def generate_gradient_backgrounds():
    """Generate iOS Weather-style gradient backgrounds using PIL.

    NOT photos — clean designed gradients exactly like Apple Weather:
    - Clear day:          bright cerulean sky blue gradient
    - Clear night:        deep midnight blue with subtle glow
    - Partly cloudy day:  sky blue, slightly muted
    - Partly cloudy night:dark blue-indigo
    - Overcast:           warm steel gray
    - Fog:                pale silver-blue mist
    - Drizzle:            muted teal-slate
    - Rain:               deep ocean blue-gray
    - Heavy rain:         charcoal-indigo dark
    - Snow:               cool ice blue
    - Thunderstorm:       near-black charcoal-purple

    All use the same 3-stop gradient formula so they look like a family.
    Size: 1080 x 420  (wide hero card format)
    """
    W, H = 1080, 420
    bg_dir = os.path.join(ASSETS_DIR, 'backgrounds')
    os.makedirs(bg_dir, exist_ok=True)

    # (name, top_rgb, mid_rgb, bottom_rgb)
    # Colours match iOS Weather's actual palette
    GRADIENTS = [
        # ── DAYTIME ──────────────────────────────────────────────────
        ('clear_day',          (74, 176, 245),  (25, 118, 210),  (13,  71, 161)),
        ('partly_cloudy_day',  (80, 162, 210),  (40, 108, 170),  (20,  65, 120)),
        ('overcast',           (110,130,145),   (78,  96,108),   (55,  70, 80)),
        ('fog',                (176,195,210),   (140,162,178),   (108,130,148)),
        ('drizzle',            (60, 110,150),   (38,  82,118),   (22,  55, 88)),
        ('rain',               (30,  62, 95),   (18,  40, 68),   (10,  22, 45)),
        ('heavy_rain',         (18,  35, 58),   (10,  22, 40),   (5,   12, 28)),
        ('snow',               (160,200,230),   (110,162,200),   (75, 128,170)),
        ('thunderstorm',       (20,  15, 35),   (10,   8, 22),   (4,   3, 12)),
        # ── NIGHTTIME ────────────────────────────────────────────────
        ('clear_night',        (5,   12, 35),   (10,  22, 60),   (18,  35, 90)),
        ('partly_cloudy_night',(8,   15, 40),   (14,  28, 65),   (22,  40, 88)),
    ]

    for name, top, mid, bot in GRADIENTS:
        img = Image.new('RGB', (W, H))
        draw = ImageDraw.Draw(img)
        half = H // 2
        for y in range(H):
            if y <= half:
                t = y / half
                r = int(top[0] + (mid[0] - top[0]) * t)
                g = int(top[1] + (mid[1] - top[1]) * t)
                b = int(top[2] + (mid[2] - top[2]) * t)
            else:
                t = (y - half) / half
                r = int(mid[0] + (bot[0] - mid[0]) * t)
                g = int(mid[1] + (bot[1] - mid[1]) * t)
                b = int(mid[2] + (bot[2] - mid[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Subtle horizon brightness for daytime (warm glow near center-bottom)
        if 'night' not in name and name not in ('thunderstorm',):
            ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            cx = W // 2
            for radius in range(260, 0, -8):
                alpha = int(18 * (1 - radius / 260))
                od.ellipse([cx - radius, H - radius//2,
                            cx + radius, H + radius//2],
                           fill=(255, 240, 200, alpha))
            ov_rgb = ov.filter(ImageFilter.GaussianBlur(radius=30))
            img = Image.alpha_composite(img.convert('RGBA'), ov_rgb).convert('RGB')

        path = os.path.join(bg_dir, f'{name}.jpg')
        img.save(path, 'JPEG', quality=96)
        print(f'  Generated {name}.jpg')

    print(f'Generated {len(GRADIENTS)} gradient backgrounds')


def download_backgrounds():
    """Download hi-res weather condition background photos for the hero card.

    Sources: Unsplash CDN (Unsplash License — free for use in apps).
    Photos are landscape-cropped to 1080×420 for the hero section.
    """
    import urllib.request
    bg_dir = os.path.join(ASSETS_DIR, 'backgrounds')
    os.makedirs(bg_dir, exist_ok=True)

    photos = {
        'clear_day':          'https://images.unsplash.com/photo-1601297183305-6df142704ea2?w=1080&h=420&fit=crop&auto=format&q=85',
        'clear_night':        'https://images.unsplash.com/photo-1475274047050-1d0c0975c63e?w=1080&h=420&fit=crop&auto=format&q=85',
        'partly_cloudy_day':  'https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1080&h=420&fit=crop&auto=format&q=85',
        'partly_cloudy_night':'https://images.unsplash.com/photo-1534003045591-ea0aba5f2a46?w=1080&h=420&fit=crop&auto=format&q=85',
        'overcast':           'https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=1080&h=420&fit=crop&auto=format&q=85',
        'fog':                'https://images.unsplash.com/photo-1487621167305-5d248087c724?w=1080&h=420&fit=crop&auto=format&q=85',
        'drizzle':            'https://images.unsplash.com/photo-1428592953211-077101b2021b?w=1080&h=420&fit=crop&auto=format&q=85',
        'rain':               'https://images.unsplash.com/photo-1501999635878-71cb5379c2d8?w=1080&h=420&fit=crop&auto=format&q=85',
        'heavy_rain':         'https://images.unsplash.com/photo-1519692933481-e162a57d6721?w=1080&h=420&fit=crop&auto=format&q=85',
        'snow':               'https://images.unsplash.com/photo-1491002052546-bf38f186af56?w=1080&h=420&fit=crop&auto=format&q=85',
        'thunderstorm':       'https://images.unsplash.com/photo-1605727216801-e27ce1d0cc28?w=1080&h=420&fit=crop&auto=format&q=85',
    }

    headers = {'User-Agent': 'kakoritz-WeatherApp/1.0'}
    downloaded = skipped = failed = 0

    for name, url in photos.items():
        path = os.path.join(bg_dir, f'{name}.jpg')
        if os.path.exists(path) and os.path.getsize(path) > 10_000:
            skipped += 1
            continue
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(path, 'wb') as f:
                    f.write(resp.read())
            print(f'  Downloaded {name}.jpg ({os.path.getsize(path)//1024}KB)')
            downloaded += 1
        except Exception as e:
            print(f'  FAILED {name}: {e}')
            failed += 1

    print(f'Backgrounds: {downloaded} downloaded, {skipped} already present, {failed} failed')


def download_weather_icons():
    """Download weather icons from Bas Milius weather-icons (MIT license).

    These are professional icons used by major weather apps.
    The sun is yellow/white — not the orange of OpenWeatherMap icons.
    Source: https://github.com/basmilius/weather-icons (MIT)
    CDN: https://raw.githubusercontent.com/basmilius/weather-icons/dev/production/fill/png/512/
    """
    import urllib.request
    icons_dir = os.path.join(ASSETS_DIR, 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    # Map OWM icon code → Bas Milius icon filename
    # We keep the OWM filename convention so the rest of the app needs no changes
    BASE = 'https://raw.githubusercontent.com/basmilius/weather-icons/dev/production/fill/png/512/'
    icon_map = {
        '01d': 'clear-day.png',
        '01n': 'clear-night.png',
        '02d': 'partly-cloudy-day.png',
        '02n': 'partly-cloudy-night.png',
        '03d': 'partly-cloudy-day.png',
        '03n': 'partly-cloudy-night.png',
        '04d': 'overcast-day.png',
        '04n': 'overcast-night.png',
        '09d': 'drizzle.png',
        '09n': 'drizzle.png',
        '10d': 'rain.png',
        '10n': 'rain.png',
        '11d': 'thunderstorms-rain.png',
        '11n': 'thunderstorms-rain.png',
        '13d': 'snow.png',
        '13n': 'snow.png',
        '50d': 'fog.png',
        '50n': 'fog.png',
    }

    headers = {'User-Agent': 'kakoritz-WeatherApp/1.0'}
    downloaded = skipped = failed = 0

    for owm_code, bm_file in icon_map.items():
        path = os.path.join(icons_dir, f'{owm_code}.png')
        # Force re-download if file is small (old OWM icons are ~1.5KB, Bas Milius are 30-80KB)
        if os.path.exists(path) and os.path.getsize(path) > 20_000:
            skipped += 1
            continue
        url = BASE + bm_file
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(path, 'wb') as f:
                f.write(data)
            print(f'  Downloaded {owm_code}.png ({len(data)//1024}KB) ← {bm_file}')
            downloaded += 1
        except Exception as e:
            print(f'  FAILED {owm_code} ({bm_file}): {e}')
            failed += 1

    print(f'Icons: {downloaded} downloaded, {skipped} already present, {failed} failed')


if __name__ == '__main__':
    print('Generating app assets...')
    make_icon()
    make_presplash()
    print()
    print()
    print('Generating iOS-style gradient backgrounds...')
    generate_gradient_backgrounds()
    print()
    print('Downloading official OpenWeatherMap weather icons...')
    download_weather_icons()
    print()
    print('Done. To force presplash refresh in next buildozer run:')
    print('  find ~/.weatherapp-build -name "presplash*" -exec rm -f {} \\;')
