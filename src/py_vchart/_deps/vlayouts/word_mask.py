"""Raster masks and glyph occupancy for deterministic shape word clouds."""

from math import ceil, cos, hypot, pi, sin, sqrt

from ..vrender import Surface

FAST_SHAPES = {
    "circle",
    "rect",
    "cardioid",
    "diamond",
    "square",
    "triangle",
    "triangleUpright",
    "triangleForward",
    "pentagon",
    "star",
}


def spiral_radius(shape, theta):
    if shape in ("circle", "rect"):
        return 1
    if shape == "cardioid":
        return 1 + sin(theta)
    if shape == "square":
        return 1 / max(abs(cos(theta)), abs(sin(theta)))
    if shape == "diamond":
        angle, coefficient = theta % (pi / 2), 1
    elif shape == "pentagon":
        angle, coefficient = (theta + 0.955) % (2 * pi / 5), 0.726543
    elif shape == "star":
        angle = (theta + 0.955) % (pi / 5)
        if (theta + 0.955) % (2 * pi / 5) >= pi / 5:
            angle = pi / 5 - angle
        coefficient = 3.07768
    else:
        rotation = 0 if shape == "triangleForward" else 3 * pi / 2
        angle, coefficient = (theta + rotation) % (2 * pi / 3), sqrt(3)
    return 1 / (cos(angle) + coefficient * sin(angle))


def raster_mask(shape, width, height):
    from numpy import frombuffer, uint8

    tile = Surface(width, height)
    ctx = tile.ctx
    if isinstance(shape, str):
        from ..vrender.images import embedded_image

        im = embedded_image(shape)
        scale = min(width / im.width, height / im.height)
        w, h = int(im.width * scale), int(im.height * scale)
        ctx.drawImage(im, (width - w) / 2, (height - h) / 2, w, h)
        data = ctx.getImageData(0, 0, width, height)
        rgba = frombuffer(bytes(data.data), dtype=uint8).reshape(height, width, 4)
        return tile, (rgba[:, :, 3] > 0) & (rgba[:, :, :3] != 255).any(axis=2)
    background = shape.get("backgroundColor", "#fff")
    tile.rect((0, 0, width, height), background)
    base = tuple(ctx.getImageData(0, 0, 1, 1).data)
    if shape.get("hollow"):
        ctx.globalCompositeOperation = "xor"
    color = shape.get("fill", "#000")
    name = shape.get("shape")
    x, y = width // 2, height // 2
    r = min(x, y)
    if shape.get("type") == "text":
        family = shape.get("fontFamily", "Microsoft YaHei")
        weight = shape.get("fontWeight", "normal")
        text = shape["text"]
        ctx.font = f"{weight} 12px {family}"
        size = min(height, int(12 * width / max(12, tile.measure(text))))
        # Canvas middle aligns the normalized typographic em box.
        from struct import unpack_from

        import skia
        from py_skia_canvas import ImageData

        from ..vrender.text import _rgba, raster_font

        face = raster_font(family, size, weight, False).refTypeface()
        table = face.copyTableData(int.from_bytes(b"OS/2", "big"))
        ascent, descent = unpack_from(">hh", bytes(table), 68) if table else (3, -1)
        baseline = size * (ascent / (ascent - descent) - 0.5)
        font = raster_font(family, size, weight, False)
        glyphs = font.textToGlyphs(text)
        run = skia.TextBlob.MakeFromPosTextH(text, font.getXPos(glyphs), 0, font)
        bitmap = skia.Surface(width, height)
        canvas = bitmap.getCanvas()

        def ink(css):
            red, green, blue, alpha = _rgba(css)
            return skia.ColorSetARGB(alpha, red, green, blue)

        canvas.clear(ink(background))
        paint = skia.Paint(Color=ink(color), AntiAlias=True)
        if shape.get("hollow"):
            paint.setBlendMode(skia.BlendMode.kXor)
        canvas.drawTextBlob(
            run, x - font.measureText(text) / 2, round(y + baseline), paint
        )
        pixels = bitmap.makeImageSnapshot().toarray(
            colorType=skia.ColorType.kRGBA_8888_ColorType
        )
        ctx.putImageData(ImageData(pixels.tobytes(), width, height), 0, 0)
    elif name == "cardioid":
        y = int(height / 2.7 * 0.4)
        r = int(min(width / 2.3, height / 2.6))
        points = []
        for i in range(100):
            a = i * 2 * pi / 100
            points.append(
                (x + r * (1 + sin(a)) * cos(a), y + r * (1 + sin(a)) * sin(a))
            )
        ctx.beginPath()
        ctx.moveTo(*points[0])
        for previous, point in zip(points, points[1:]):
            ctx.bezierCurveTo(*point, *previous, *point)
        ctx.closePath()
        ctx.fillStyle = color
        ctx.fill()
    elif name == "circle":
        tile.circle(x, y, r * 2, color, None, 0)
    else:
        polygons = {
            "diamond": (4, -pi / 2),
            "square": (4, -pi / 4),
            "pentagon": (5, pi / 2),
            "star": (10, -pi / 2),
            "triangle": (3, -pi / 2),
            "triangleUpright": (3, -pi / 2),
            "triangleForward": (3, 0),
        }
        if name not in polygons:
            raise ValueError(f"Unsupported geometric mask {name}")
        if name in ("triangle", "triangleUpright"):
            y = int(height / 1.5)
            r = int(min(height / 1.5, width / 2))
        if name == "triangleForward":
            r = int(min(width / 2, height / sqrt(3)))
        count, offset = polygons[name]
        points = []
        for i in range(count):
            angle = offset + 2 * pi * i / count
            radius = r / (2 * cos(pi / 5)) if name == "star" and i % 2 else r
            points.append((x + radius * cos(angle), y + radius * sin(angle)))
        tile.polygon_rings([points], color, None, 0)
    data = ctx.getImageData(0, 0, width, height)
    rgba = frombuffer(bytes(data.data), dtype=uint8).reshape(height, width, 4)
    allowed = (rgba != base).any(axis=2)
    if background == "#fff":
        allowed &= rgba[:, :, 3] > 0
    return tile, allowed


class MaskBoard:
    def __init__(self, allowed):
        import numpy as np

        self.available = allowed.copy()
        padded = np.pad(allowed, 1)
        interior = (
            padded[1:-1, :-2] & padded[1:-1, 2:] & padded[:-2, 1:-1] & padded[2:, 1:-1]
        )
        y, x = np.where(allowed & ~interior)
        self.bounds = (
            (int(x.min()), int(y.min()), int(x.max()), int(y.max()))
            if x.size
            else (0, 0, -1, -1)
        )
        self.area = int(allowed.sum())
        self.center = (int(x.mean()), int(y.mean())) if x.size else (0, 0)
        self.ratio = (
            (int(x.max()) - int(x.min())) / max(1, int(y.max()) - int(y.min()))
            if x.size
            else 1
        )

    def regions(self):
        """Find four-connected components using horizontal runs."""
        from collections import defaultdict

        import numpy as np

        parent = []

        def root(i):
            while i != parent[i]:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        runs = []
        previous = []
        for y, row in enumerate(self.available):
            edges = np.flatnonzero(np.diff(np.pad(row, (1, 1))))
            current = []
            j = 0
            for left, right in edges.reshape(-1, 2):
                left, right = int(left), int(right)
                i = len(parent)
                parent.append(i)
                while j < len(previous) and previous[j][1] <= left:
                    j += 1
                k = j
                while k < len(previous) and previous[k][0] < right:
                    parent[root(i)] = root(previous[k][2])
                    k += 1
                current.append((left, right, i))
                runs.append((y, left, right, i))
            previous = current
        groups = defaultdict(list)
        for y, l, r, i in runs:
            groups[root(i)].append((y, l, r))
        if len(groups) == 1:
            return [(self.center, self.ratio, self.area)]
        result = []
        for rows in groups.values():
            y0 = rows[0][0]
            x0 = min(l for _, l, _ in rows)
            region = np.zeros(
                (rows[-1][0] - y0 + 1, max(r for _, _, r in rows) - x0), bool
            )
            for y, l, r in rows:
                region[y - y0, l - x0 : r - x0] = True
            local = MaskBoard(region)
            result.append(
                ((x0 + local.center[0], y0 + local.center[1]), local.ratio, local.area)
            )
        return result

    def word_regions(self, sizes):
        regions = self.regions()
        if not regions:
            return [None] * len(sizes)
        largest = max(range(len(regions)), key=lambda i: regions[i][2])
        quotas = [ceil(area / self.area * len(sizes)) for _, _, area in regions]
        limits = [area / regions[largest][2] for _, _, area in regions]
        chosen = []
        i = largest
        max_size = max(sizes, default=1)
        for size in sizes:
            for attempt in range(3 * len(regions)):
                if quotas[i] > 0 and size / max_size <= limits[i]:
                    break
                i = (i + 1) % len(regions)
                if attempt == len(regions) + 1:
                    limits = [v + 0.15 for v in limits]
            else:
                i = largest
            chosen.append(regions[i][:2])
            quotas[i] -= 1
            i = (i + 1) % len(regions)
        return chosen

    def place(self, offsets, step, region=None):
        dy, dx = offsets
        if not dx.size:
            return None
        h, w = self.available.shape
        (x0, y0), ratio = region or (self.center, self.ratio)
        xmin, xmax, ymin, ymax = dx.min(), dx.max(), dy.min(), dy.max()
        limit = hypot(w, h) / min(1, max(ratio, 0.01))
        for i in range(ceil(limit / (step * 0.1)) + 1):
            t = i * step * 0.1
            x = int(x0 + ratio * t * cos(t))
            y = int(y0 + t * sin(t))
            if x + xmin < 0 or x + xmax >= w or y + ymin < 0 or y + ymax >= h:
                continue
            if self.available[y + dy, x + dx].all():
                self.available[y + dy, x + dx] = False
                return x, y
        return None


def glyph_offsets(text, family, weight, size, width, angle, padding):
    import numpy as np
    import skia

    from ..vrender.text import raster_font

    half = ceil(hypot(width + 2 * padding, 2 * size + 2 * padding) / 2) + 3
    tile = skia.Surface(2 * half, 2 * half)
    ctx = tile.getCanvas()
    ctx.translate(half, half)
    ctx.rotate(angle * 180 / pi)
    font = raster_font(family, size, weight)
    run = skia.TextBlob.MakeFromPosTextH(
        text, font.getXPos(font.textToGlyphs(text)), 0, font
    )
    x = -font.measureText(text) / 2
    ctx.drawTextBlob(run, x, 0, skia.Paint(AntiAlias=True))
    if padding:
        ctx.drawTextBlob(
            run,
            x,
            0,
            skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=2 * padding,
                StrokeMiter=10,
            ),
        )
    y, x = np.where(tile.makeImageSnapshot().toarray()[:, :, 3] > 0)
    # Atlas cells clip ink (in particular miter tips on very small type).
    cell_w = font.measureText(text + "m") + 2 * padding
    cell_h = 2 * size + 2 * padding
    if angle:
        c, s = abs(cos(angle)), abs(sin(angle))
        cell_w, cell_h = c * cell_w + s * cell_h, int(s * cell_w + c * cell_h)
    cell_w = (int(cell_w + 31) // 32) * 32
    cell_h = ceil(cell_h)
    dy, dx = y - half, x - half
    inside = (
        (dy >= -(cell_h // 2))
        & (dy < cell_h - cell_h // 2)
        & (dx >= -(cell_w // 2))
        & (dx < cell_w - cell_w // 2)
    )
    return dy[inside], dx[inside]


def filling_layout(board, words, options, font_family, weight, padding):
    """Scan the native grid in rows, reusing padded glyphs for repeated words."""
    from itertools import cycle
    from math import radians

    from ..vrender.text import raster_font

    times = options.get("fillingTimes", 4)
    if not words or not times:
        return
    random = cycle(i / 10 for i in range(10)).__next__
    for _ in words:
        random()  # primary-word rotation selection
    angles = options.get("fillingRotateAngles", [0])
    size = options.get("fillingInitialFontSize")
    delta = options.get("fillingDeltaFontSize")
    if not size or not delta:
        lengths = [
            sum(1 if "\u4e00" <= c <= "\u9fff" else 0.53 for c in t) for t, ok in words
        ]
        length = sum(v for v in lengths if v <= ceil(sqrt(board.area) / 4)) / len(words)
        initial = (
            sqrt(options.get("fillingRatio", 0.7) * board.area * 0.002 / length)
            if length
            else 8
        )
        size = int(initial)
        delta = initial * options.get("fillingDeltaFontSizeFactor", 0.2)
    x0, y0, x1, y1 = board.bounds
    h, w = board.available.shape

    def grid(axis, extent):
        ratio = options.get("filling" + axis + "RatioStep")
        return (
            max(1, int(extent * ratio))
            if ratio
            else max(1, options.get("filling" + axis + "Step", 4))
        )

    sx, sy = grid("X", w), grid("Y", h)

    def shuffle(items):
        # V8 uses insertion sort for short arrays. Its comparison order
        # consumes the deterministic random stream that also sets grid offsets.
        for i in range(1, len(items)):
            item = items[i]
            j = i
            while j and random() < 0.5:
                items[j] = items[j - 1]
                j -= 1
            items[j] = item

    for _ in range(times):
        candidates = []
        for text, placed in words:
            angle = radians(angles[int(random() * len(angles))])
            measured = max(2, size)
            width = raster_font(font_family, measured, weight, False).measureText(text)
            dy, dx = glyph_offsets(
                text, font_family, weight, measured, width, angle, padding
            )
            bounds = (
                (int(dx.min()), int(dy.min()), int(dx.max()), int(dy.max()))
                if dx.size
                else None
            )
            candidates.append((text, angle, dy, dx, bounds, placed))
        shuffle(candidates)
        start_x = x0 + int(random() * sx * 2)
        start_y = y0 + int(random() * sy * 2)
        i = 0
        for y in range(start_y, y1 + 1, sy):
            for x in range(start_x, x1 + 1, sx):
                text, angle, dy, dx, bounds, placed = candidates[i]
                if placed and bounds:
                    l, t, r, b = bounds
                    if (
                        x + l < 0
                        or x + r >= w
                        or y + t < 0
                        or y + b >= h
                        or not board.available[y + dy, x + dx].all()
                    ):
                        continue
                    board.available[y + dy, x + dx] = False
                    yield text, x, y, size, angle
                i += 1
                if i == len(candidates):
                    i = 0
                    if options.get("random", True):
                        shuffle(candidates)
        size = max(
            size - delta if size > delta else delta, options.get("minFillFontSize", 2)
        )
