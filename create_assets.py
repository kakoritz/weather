"""Generate assets/icon.png (512×512), assets/presplash.jpg (1080×1920),
and versioned copies in assets/versions/.

Run once before building the APK:
    python3 create_assets.py

After changing presplash, bust the p4a cache before rebuilding:
    find ~/.weatherapp-build -name "presplash*" -exec rm -f {} \\;

Requirements: pillow  (pip install pillow)
Notes:
  - icon must be PNG (buildozer scales it)
  - presplash MUST be JPG — p4a silently ignores .png presplash
"""
import math
import os
import shutil

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    raise SystemExit('Pillow is required: pip install pillow')

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
VERSIONS_DIR = os.path.join(ASSETS_DIR, 'versions')
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)


# ─── versioning ────────────────────────────────────────────────────────────────

def archive_assets(label):
    """Copy current icon/presplash to assets/versions/{label}/ before overwriting."""
    dest = os.path.join(VERSIONS_DIR, label)
    os.makedirs(dest, exist_ok=True)
    archived = []
    for fname in ('icon.png', 'icon_bg.png', 'icon_fg.png', 'presplash.jpg'):
        src = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, fname))
            archived.append(fname)
    if archived:
        print(f'Archived {len(archived)} assets → assets/versions/{label}/')
    return bool(archived)


def _save_version_copy(label):
    """After generation, copy fresh assets to assets/versions/{label}/ too."""
    dest = os.path.join(VERSIONS_DIR, label)
    os.makedirs(dest, exist_ok=True)
    for fname in ('icon.png', 'icon_bg.png', 'icon_fg.png', 'presplash.jpg'):
        src = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, fname))
    print(f'Saved version copy → assets/versions/{label}/')


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


# ─── bird silhouette ───────────────────────────────────────────────────────────

def _bird_polygon(cx, cy, span):
    """Polygon points for a stylized soaring swift/swallow silhouette.

    Forked tail, swept-back wings — readable at any size down to 48px.
    cx, cy: centre of the bird body
    span:   tip-to-tip wingspan in pixels
    """
    s = span / 2
    return [
        (cx + s,         cy + s * 0.05),   # right wingtip
        (cx + s * 0.60,  cy - s * 0.22),   # right outer wing upper
        (cx + s * 0.18,  cy - s * 0.28),   # right inner wing upper
        (cx,             cy - s * 0.15),   # body top
        (cx - s * 0.18,  cy - s * 0.28),   # left inner wing upper
        (cx - s * 0.60,  cy - s * 0.22),   # left outer wing upper
        (cx - s,         cy + s * 0.05),   # left wingtip
        (cx - s * 0.62,  cy + s * 0.12),   # left outer wing lower
        (cx - s * 0.20,  cy + s * 0.08),   # left inner wing lower
        (cx - s * 0.12,  cy + s * 0.32),   # tail left feather
        (cx,             cy + s * 0.16),   # tail centre notch (forked)
        (cx + s * 0.12,  cy + s * 0.32),   # tail right feather
        (cx + s * 0.20,  cy + s * 0.08),   # right inner wing lower
        (cx + s * 0.62,  cy + s * 0.12),   # right outer wing lower
    ]


def _draw_bird(img, cx, cy, span, color, shadow_color=None, shadow_blur=8):
    """Composite a bird silhouette (with optional drop shadow) onto an RGBA image.

    Returns the composited RGBA image.
    """
    if shadow_color:
        shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.polygon(_bird_polygon(cx + shadow_blur // 2, cy + shadow_blur, span),
                   fill=shadow_color)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        img = Image.alpha_composite(img, shadow_layer)

    bird_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bird_layer)
    bd.polygon(_bird_polygon(cx, cy, span), fill=color)
    return Image.alpha_composite(img, bird_layer)


# ─── presplash ─────────────────────────────────────────────────────────────────

def make_presplash():
    W, H = 1440, 3200

    # ── sky gradient (scanline) ───────────────────────────────────────────────
    sky = Image.new('RGB', (W, H))
    sky_draw = ImageDraw.Draw(sky)

    sky_stops = [
        (0.00, (8,  48, 118)),
        (0.28, (18, 86, 188)),
        (0.56, (52, 142, 225)),
        (0.76, (120, 195, 238)),
        (0.90, (172, 220, 245)),
        (1.00, (205, 233, 250)),
    ]

    HORIZON_Y = 1340
    SUN_CX, SUN_CY = W // 2, 730

    for y in range(H):
        frac = y / HORIZON_Y if y < HORIZON_Y else 1.0
        r, g, b = _gradient_color(min(frac, 1.0), sky_stops)

        dy = abs(y - SUN_CY)
        glow_t = max(0.0, 1.0 - dy / 700) ** 2.0
        r = min(255, r + int(72 * glow_t))
        g = min(255, g + int(46 * glow_t))
        b = max(0,   b - int(28 * glow_t))

        sky_draw.line([(0, y), (W, y)], fill=(r, g, b))

    img = sky.convert('RGBA')

    # ── sun halo ──────────────────────────────────────────────────────────────
    for radius, alpha in [(520, 18), (380, 32), (280, 52), (200, 85), (148, 130)]:
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse(
            [SUN_CX - radius, SUN_CY - radius, SUN_CX + radius, SUN_CY + radius],
            fill=(255, 225, 90, alpha),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=radius // 5))
        img = Image.alpha_composite(img, glow)

    # ── sun rays ──────────────────────────────────────────────────────────────
    RAY_INNER, RAY_OUTER, RAY_WIDTH = 148, 460, 6

    ray_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ray_draw = ImageDraw.Draw(ray_layer)

    for i in range(16):
        angle = math.radians(i * (360 / 16) - 90)
        al = angle - math.radians(RAY_WIDTH)
        ar = angle + math.radians(RAY_WIDTH)
        bx1 = SUN_CX + math.cos(al) * RAY_INNER
        by1 = SUN_CY + math.sin(al) * RAY_INNER
        bx2 = SUN_CX + math.cos(ar) * RAY_INNER
        by2 = SUN_CY + math.sin(ar) * RAY_INNER
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
    sun_draw.ellipse(
        [SUN_CX - SUN_R - 22, SUN_CY - SUN_R - 22,
         SUN_CX + SUN_R + 22, SUN_CY + SUN_R + 22],
        fill=(255, 235, 100, 180),
    )
    sun_draw.ellipse(
        [SUN_CX - SUN_R, SUN_CY - SUN_R, SUN_CX + SUN_R, SUN_CY + SUN_R],
        fill=(255, 248, 180, 255),
    )
    sun_draw.ellipse(
        [SUN_CX - SUN_R // 2, SUN_CY - SUN_R // 2,
         SUN_CX + SUN_R // 2, SUN_CY + SUN_R // 2],
        fill=(255, 255, 230, 255),
    )
    img = Image.alpha_composite(img, sun_layer)

    # ── WeatherBird — bird soaring in front of the sun ────────────────────────
    # Dark silhouette over the bright sun disc; the bird "owns" the sun.
    BIRD_CX, BIRD_CY = SUN_CX, SUN_CY   # centred on sun disc
    BIRD_SPAN = 360

    img = _draw_bird(
        img, BIRD_CX, BIRD_CY, BIRD_SPAN,
        color=(16, 28, 68, 245),
        shadow_color=(0, 0, 0, 80),
        shadow_blur=12,
    )

    # ── clouds ────────────────────────────────────────────────────────────────
    def draw_cloud(layer, cx, cy, sc, alpha=220):
        ld = ImageDraw.Draw(layer)
        def puff(x, y, rx, ry):
            ld.ellipse([cx + x - rx*sc, cy + y - ry*sc,
                        cx + x + rx*sc, cy + y + ry*sc],
                       fill=(245, 252, 255, alpha))
        ld.rectangle([cx - 110*sc, cy - 18*sc, cx + 110*sc, cy + 22*sc],
                     fill=(245, 252, 255, alpha))
        puff(-72, -22, 42, 38)
        puff(-30, -38, 52, 48)
        puff( 20, -46, 58, 52)
        puff( 74, -28, 46, 40)
        puff(108, -10, 32, 28)

    cl1 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_cloud(cl1, cx=260, cy=410, sc=1.05, alpha=210)
    cl1 = cl1.filter(ImageFilter.GaussianBlur(radius=3))
    img = Image.alpha_composite(img, cl1)

    cl2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_cloud(cl2, cx=820, cy=310, sc=0.85, alpha=195)
    cl2 = cl2.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(img, cl2)

    # ── mountain silhouettes ──────────────────────────────────────────────────
    img = img.convert('RGB')
    mtn_draw = ImageDraw.Draw(img)

    def mountain_range(peaks, base_y, color):
        poly = [(0, base_y)]
        for cx, peak_y, hw in peaks:
            poly.append((cx - hw, base_y))
            poly.append((cx, peak_y))
            poly.append((cx + hw, base_y))
        poly += [(W, base_y), (W, H), (0, H)]
        mtn_draw.polygon(poly, fill=color)

    far_peaks = [
        (120, HORIZON_Y - 210, 200), (310, HORIZON_Y - 295, 180),
        (520, HORIZON_Y - 240, 220), (720, HORIZON_Y - 310, 195),
        (880, HORIZON_Y - 255, 210), (1040, HORIZON_Y - 180, 165),
    ]
    mountain_range(far_peaks, HORIZON_Y, (58, 82, 140))

    mid_peaks = [
        (-30, HORIZON_Y - 160, 190),  (185, HORIZON_Y - 245, 200),
        (420, HORIZON_Y - 285, 210),  (640, HORIZON_Y - 230, 185),
        (830, HORIZON_Y - 270, 200),  (1050, HORIZON_Y - 155, 175),
        (1150, HORIZON_Y - 120, 160),
    ]
    mountain_range(mid_peaks, HORIZON_Y + 60, (38, 52, 105))

    near_peaks = [
        (-50,  HORIZON_Y + 10, 220),  (180,  HORIZON_Y - 115, 230),
        (440,  HORIZON_Y - 140, 240), (680,  HORIZON_Y - 100, 210),
        (870,  HORIZON_Y - 135, 225), (1080, HORIZON_Y - 80,  200),
        (1200, HORIZON_Y + 20, 190),
    ]
    mountain_range(near_peaks, HORIZON_Y + 120, (22, 30, 72))

    snow_color = (225, 238, 252)
    for cx, py, hw in far_peaks:
        cap_h = int(hw * 0.22)
        cap_w = int(hw * 0.28)
        mtn_draw.polygon([
            (cx - cap_w, py + cap_h + 8),
            (cx, py),
            (cx + cap_w, py + cap_h + 8),
        ], fill=snow_color)

    mtn_draw.rectangle([0, HORIZON_Y + 180, W, H], fill=(14, 20, 52))

    img_rgba = img.convert('RGBA')
    haze = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    haze_draw = ImageDraw.Draw(haze)
    for hy in range(HORIZON_Y - 80, HORIZON_Y + 60):
        t = max(0.0, 1.0 - abs(hy - HORIZON_Y) / 80.0)
        haze_draw.line([(0, hy), (W, hy)], fill=(200, 230, 255, int(38 * t)))
    img = Image.alpha_composite(img_rgba, haze).convert('RGB')

    # ── text — WeatherBird branding ───────────────────────────────────────────
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

    font_main = load_font(font_paths, 110)
    font_sub  = load_font(font_paths_reg, 54)

    def draw_text_centered(text, font, y, color, shadow_color=(0, 0, 0, 150)):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x + 3, y + 4), text, font=font, fill=shadow_color)
        draw.text((x, y), text, font=font, fill=color)

    draw_text_centered('WeatherBird', font_main, y=1660, color=(255, 255, 255))
    draw_text_centered('even birds need a forecast', font_sub, y=1800,
                       color=(180, 215, 255))

    path = os.path.join(ASSETS_DIR, 'presplash.jpg')
    img.save(path, 'JPEG', quality=96)
    print(f'Created {path}')


# ─── app icon ──────────────────────────────────────────────────────────────────

def make_icon():
    """App icon: sky-blue background, sun with rays, WeatherBird silhouette.

    The bird is a dark navy silhouette positioned to overlap the top of the sun
    — visually it "owns" the sun. Android adaptive icon system crops to circle.
    """
    SIZE = 512
    CX = CY = SIZE // 2

    img = Image.new('RGBA', (SIZE, SIZE), (52, 152, 235, 255))

    # ── Sun glow ───────────────────────────────────────────────────────────────
    for r, a in [(240, 12), (210, 25), (180, 45), (155, 75), (130, 110)]:
        glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([CX-r, CY-r, CX+r, CY+r], fill=(255, 235, 90, a))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=r // 5))
        img = Image.alpha_composite(img, glow)

    # ── Sun rays ───────────────────────────────────────────────────────────────
    RAY_INNER, RAY_OUTER, RAY_HALF = 155, 248, 7

    rays = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        al = angle - math.radians(RAY_HALF)
        ar = angle + math.radians(RAY_HALF)
        bx1 = CX + math.cos(al) * RAY_INNER
        by1 = CY + math.sin(al) * RAY_INNER
        bx2 = CX + math.cos(ar) * RAY_INNER
        by2 = CY + math.sin(ar) * RAY_INNER
        tx  = CX + math.cos(angle) * RAY_OUTER
        ty  = CY + math.sin(angle) * RAY_OUTER
        rd.polygon([(bx1, by1), (bx2, by2), (tx, ty)],
                   fill=(255, 248, 160, 200))
    rays = rays.filter(ImageFilter.GaussianBlur(radius=5))
    img = Image.alpha_composite(img, rays)

    # ── Sun disc ───────────────────────────────────────────────────────────────
    sun = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun)
    R = 140
    sd.ellipse([CX-R-20, CY-R-20, CX+R+20, CY+R+20], fill=(255, 230, 80, 210))
    sd.ellipse([CX-R,    CY-R,    CX+R,    CY+R   ], fill=(255, 248, 140, 255))
    sd.ellipse([CX-R//2, CY-R//2, CX+R//2, CY+R//2], fill=(255, 255, 230, 255))
    img = Image.alpha_composite(img, sun)

    # ── WeatherBird silhouette ─────────────────────────────────────────────────
    # Dark navy bird, body centred just above the sun centre so it sits
    # visibly against the bright disc. Forked tail dips into the glow.
    img = _draw_bird(
        img, CX, CY, span=200,
        color=(16, 28, 68, 250),
        shadow_color=(0, 0, 0, 90),
        shadow_blur=6,
    )

    # ── Save legacy icon ───────────────────────────────────────────────────────
    path = os.path.join(ASSETS_DIR, 'icon.png')
    img.save(path, 'PNG')
    print(f'Created {path}')

    # ── Adaptive icon background layer (solid sky blue) ───────────────────────
    bg = Image.new('RGB', (512, 512), (52, 152, 235))
    bg_path = os.path.join(ASSETS_DIR, 'icon_bg.png')
    bg.save(bg_path, 'PNG')
    print(f'Created {bg_path}')

    # ── Adaptive icon foreground layer (sun + bird on transparent bg) ─────────
    fg = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    FCX = FCY = 256

    # Glow rings within safe zone (84px margin → content within 84–428 px)
    for r, a in [(145, 18), (125, 38), (108, 65), (92, 100)]:
        fg_glow = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        fgd = ImageDraw.Draw(fg_glow)
        fgd.ellipse([FCX-r, FCY-r, FCX+r, FCY+r], fill=(255, 235, 90, a))
        fg_glow = fg_glow.filter(ImageFilter.GaussianBlur(radius=r // 5))
        fg = Image.alpha_composite(fg, fg_glow)

    # Rays (stay within safe zone: outer 155px from centre)
    fg_rays = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    frd = ImageDraw.Draw(fg_rays)
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        al = angle - math.radians(7)
        ar = angle + math.radians(7)
        bx1 = FCX + math.cos(al) * 92
        by1 = FCY + math.sin(al) * 92
        bx2 = FCX + math.cos(ar) * 92
        by2 = FCY + math.sin(ar) * 92
        tx  = FCX + math.cos(angle) * 155
        ty  = FCY + math.sin(angle) * 155
        frd.polygon([(bx1, by1), (bx2, by2), (tx, ty)], fill=(255, 248, 160, 200))
    fg_rays = fg_rays.filter(ImageFilter.GaussianBlur(radius=4))
    fg = Image.alpha_composite(fg, fg_rays)

    # Sun disc
    fg_sun = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    fsd = ImageDraw.Draw(fg_sun)
    fsd.ellipse([FCX-82, FCY-82, FCX+82, FCY+82], fill=(255, 230, 80, 210))
    fsd.ellipse([FCX-78, FCY-78, FCX+78, FCY+78], fill=(255, 248, 140, 255))
    fsd.ellipse([FCX-40, FCY-40, FCX+40, FCY+40], fill=(255, 255, 230, 255))
    fg = Image.alpha_composite(fg, fg_sun)

    # Bird on foreground (same dark navy, scaled to safe zone)
    fg = _draw_bird(
        fg, FCX, FCY, span=160,
        color=(16, 28, 68, 250),
        shadow_color=(0, 0, 0, 80),
        shadow_blur=5,
    )

    fg_path = os.path.join(ASSETS_DIR, 'icon_fg.png')
    fg.save(fg_path, 'PNG')
    print(f'Created {fg_path}')


# ─── gradient backgrounds ──────────────────────────────────────────────────────

def generate_gradient_backgrounds():
    """Generate iOS Weather-style gradient backgrounds using PIL."""
    W, H = 1080, 420
    bg_dir = os.path.join(ASSETS_DIR, 'backgrounds')
    os.makedirs(bg_dir, exist_ok=True)

    GRADIENTS = [
        ('clear_day',          (74, 176, 245),  (25, 118, 210),  (13,  71, 161)),
        ('partly_cloudy_day',  (80, 162, 210),  (40, 108, 170),  (20,  65, 120)),
        ('overcast',           (110,130,145),   (78,  96,108),   (55,  70, 80)),
        ('fog',                (176,195,210),   (140,162,178),   (108,130,148)),
        ('drizzle',            (60, 110,150),   (38,  82,118),   (22,  55, 88)),
        ('rain',               (30,  62, 95),   (18,  40, 68),   (10,  22, 45)),
        ('heavy_rain',         (18,  35, 58),   (10,  22, 40),   (5,   12, 28)),
        ('snow',               (160,200,230),   (110,162,200),   (75, 128,170)),
        ('thunderstorm',       (20,  15, 35),   (10,   8, 22),   (4,   3, 12)),
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


# ─── background photos ─────────────────────────────────────────────────────────

def download_backgrounds():
    """Download hi-res weather condition background photos for the hero card.

    Sources: Unsplash CDN (Unsplash License — free for use in apps).
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

    headers = {'User-Agent': 'kakoritz-WeatherBird/1.4'}
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


# ─── weather icons ─────────────────────────────────────────────────────────────

def download_weather_icons():
    """Download weather icons from Bas Milius weather-icons (MIT license).

    Source: https://github.com/basmilius/weather-icons (MIT)
    CDN: https://raw.githubusercontent.com/basmilius/weather-icons/dev/production/fill/png/512/
    """
    import urllib.request
    icons_dir = os.path.join(ASSETS_DIR, 'icons')
    os.makedirs(icons_dir, exist_ok=True)

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

    headers = {'User-Agent': 'kakoritz-WeatherBird/1.4'}
    downloaded = skipped = failed = 0

    for owm_code, bm_file in icon_map.items():
        path = os.path.join(icons_dir, f'{owm_code}.png')
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


# ─── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('Archiving previous assets...')
    archive_assets('v1.3-sun')

    print('\nGenerating WeatherBird assets...')
    make_icon()
    make_presplash()

    print('\nSaving version snapshot...')
    _save_version_copy('v1.4-weatherbird')

    print('\nGenerating iOS-style gradient backgrounds...')
    generate_gradient_backgrounds()

    print('\nDownloading weather icons...')
    download_weather_icons()

    print('\nDone.')
    print('Browse assets at: assets/versions/ (old and new side by side)')
    print('To force presplash refresh in next buildozer run:')
    print('  find ~/.weatherapp-build -name "presplash*" -exec rm -f {} \\;')
