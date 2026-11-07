"""Small Canvas 2D adapter for the static Cartesian renderer."""

from math import atan2, ceil, cos, floor, pi, sin, tan, tau

FONT = '12px "Microsoft YaHei", "Segoe UI", Arial, sans-serif'


class Surface:
    def __init__(self, width, height, *, text_contrast=0):
        try:
            from py_skia_canvas import Canvas
        except ImportError as exc:
            raise RuntimeError("Install py-visactor-vchart[render] with CPython 3.13") from exc
        self.canvas = Canvas(width, height, {"textContrast": text_contrast})
        # Pin offscreen rasterization across machines and driver configurations.
        self.canvas.gpu = False
        self.ctx = self.canvas.getContext("2d")
        self.ctx.font = FONT
        self.labels = []

    def measure(self, text):
        return self.ctx.measureText(str(text)).width

    def rect(self, box, color):
        x, y, right, bottom = box
        self.ctx.fillStyle = color
        self.ctx.fillRect(x, y, right - x, bottom - y)

    def line(self, x1, y1, x2, y2, color):
        self.ctx.strokeStyle = color
        self.ctx.beginPath()
        self.ctx.moveTo(x1, y1)
        self.ctx.lineTo(x2, y2)
        self.ctx.stroke()

    def polyline(self, points, color, width):
        if len(points) < 2 or not width:
            return
        ctx = self.ctx
        ctx.save()
        ctx.strokeStyle = color
        ctx.lineWidth = width
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        ctx.beginPath()
        ctx.moveTo(*points[0])
        for point in points[1:]:
            ctx.lineTo(*point)
        ctx.stroke()
        ctx.restore()

    def sector(self, x, y, inner, outer, start, end, color, opacity=1, *, stroke=None):
        if outer <= 0 or start == end:
            return
        ctx = self.ctx
        ctx.save()
        ctx.beginPath()
        ctx.arc(x, y, outer, start, end, end < start)
        # Stroke the contours of a full disk or annulus without a radial seam.
        full_outline = stroke and abs(end-start) >= tau-1e-12
        if inner:
            if full_outline:
                ctx.closePath()
                ctx.moveTo(x+inner*cos(end), y+inner*sin(end))
            ctx.arc(x, y, inner, end, start, end >= start)
        elif not full_outline:
            ctx.lineTo(x, y)
        ctx.closePath()
        ctx.fillStyle = color
        ctx.globalAlpha = opacity
        ctx.fill()
        if stroke:
            ctx.strokeStyle = stroke
            ctx.stroke()
        ctx.restore()

    def polygon_rings(self, rings, fill, stroke, width):
        ctx = self.ctx
        ctx.save()
        ctx.beginPath()
        for ring in rings:
            ctx.moveTo(*ring[0])
            for point in ring[1:]:
                ctx.lineTo(*point)
            ctx.closePath()
        if width and stroke:
            ctx.strokeStyle = stroke
            ctx.lineWidth = width
            ctx.stroke()
        ctx.fillStyle = fill
        ctx.fill()
        ctx.restore()

    def flow_band(self, x0, y0, x1, y1, thickness, origin, vertical, color, opacity):
        def point(x, y):
            return (y, x) if vertical else (x, y)

        def pixel(value):
            return floor(value + 0.5)

        mid = pixel((x0+x1)/2)
        x0, x1 = pixel(x0), pixel(x1)
        top0, top1 = pixel(y0-thickness/2), pixel(y1-thickness/2)
        bottom0, bottom1 = pixel(top0+thickness), pixel(top1+thickness)
        ctx = self.ctx
        ctx.save()
        ctx.translate(*origin)
        ctx.beginPath()
        ctx.moveTo(*point(x0, top0))
        ctx.bezierCurveTo(*point(mid, top0), *point(mid, top1), *point(x1, top1))
        ctx.lineTo(*point(x1, bottom1))
        ctx.bezierCurveTo(*point(mid, bottom1), *point(mid, bottom0), *point(x0, bottom0))
        ctx.closePath()
        ctx.fillStyle = color
        ctx.globalAlpha = opacity
        ctx.fill()
        ctx.restore()

    def polygon(self, points, color, opacity=1):
        if len(points) < 3:
            return
        ctx = self.ctx
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(*points[0])
        for point in points[1:]:
            ctx.lineTo(*point)
        ctx.closePath()
        ctx.fillStyle = color
        ctx.globalAlpha = floor(opacity * 255 + 0.5) / 255
        ctx.fill()
        ctx.restore()

    def outline(self, box, color, width=1):
        x, y, right, bottom = box
        ctx = self.ctx
        ctx.save()
        ctx.strokeStyle = color
        ctx.lineWidth = width
        ctx.strokeRect(x, y, right - x, bottom - y)
        ctx.restore()

    def fill_arc_path(self, arcs, color, opacity):
        """Fill a closed chain of counterclockwise circular arcs as cubic segments."""
        ctx = self.ctx
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(*arcs[0].start)
        for arc in arcs:
            c = arc.circle
            count = max(1, ceil(arc.sweep/(pi/2+.001)))
            step = -arc.sweep/count
            handle = 4/3*tan(step/4)*c.r
            angle = atan2(arc.start[1]-c.y, arc.start[0]-c.x)
            for _ in range(count):
                end = angle+step
                x, y = c.x+c.r*cos(angle), c.y+c.r*sin(angle)
                u, v = c.x+c.r*cos(end), c.y+c.r*sin(end)
                ctx.bezierCurveTo(x-handle*sin(angle), y+handle*cos(angle),
                                  u+handle*sin(end), v-handle*cos(end), u, v)
                angle = end
        ctx.closePath()
        ctx.fillStyle = color
        ctx.globalAlpha = floor(opacity*255+.5)/255
        ctx.fill()
        ctx.restore()

    def circle(self, x, y, diameter, fill, stroke, width, fill_opacity=1):
        if not diameter:
            return
        ctx = self.ctx
        ctx.save()
        ctx.beginPath()
        ctx.arc(x, y, diameter / 2, 0, tau)
        # Chromium quantizes global alpha to an 8-bit coverage value.
        ctx.globalAlpha = floor(fill_opacity * 255 + 0.5) / 255
        ctx.fillStyle = fill
        ctx.fill()
        if width:
            ctx.globalAlpha = 1
            ctx.lineWidth = width
            ctx.strokeStyle = stroke
            ctx.stroke()
        ctx.restore()

    def label(self, text, x, y, align, baseline, *, line_height=None):
        self.labels.append(dict(text=str(text), x=x, y=y, align=align, baseline=baseline))
        self.ctx.fillStyle = "#89909d"
        if line_height is not None:
            advance = self.measure(text)
            left = x - {"left": 0, "center": advance/2, "right": advance}[align]
            bottom = y + {"top": line_height, "middle": line_height/2, "bottom": 0}[baseline]
            self.ctx.textAlign = "left"
            self.ctx.textBaseline = "alphabetic"
            self.ctx.fillText(str(text), left, bottom - 1)
            return
        self.ctx.textAlign = align
        self.ctx.textBaseline = baseline
        self.ctx.fillText(str(text), x, y - 2 if baseline == "top" else floor(y + 0.5))

    def png(self):
        return self.canvas.toBufferSync("png")
