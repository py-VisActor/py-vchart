"""Static image marks, fitted SVG sources and image-cloud spiral packing."""

from math import cos, hypot, sin, sqrt
from xml.etree import ElementTree

from .._deps.vrender.images import embedded_image
from .cartesian import check_keys
from .layout_helpers import field, records

ElementTree.register_namespace("", "http://www.w3.org/2000/svg")
_svg_sources = {}


def register_svg_source(name, source):
    root = ElementTree.fromstring(source)
    if root.tag.split("}")[-1] != "svg":
        raise ValueError("pictogram source must be SVG")
    _svg_sources[name] = root


def render_pictogram(spec, surface, width, height):
    from copy import deepcopy

    import numpy as np
    import skia
    from py_skia_canvas import ImageData

    rows = records(
        spec, {"svg", "nameField", "valueField", "pictogram", "defaultFillColor"}
    )
    root = _svg_sources.get(spec["svg"])
    if root is None:
        raise ValueError(f"Unregistered pictogram SVG: {spec['svg']}")
    view = root.get("viewBox", f"0 0 {root.get('width', 0)} {root.get('height', 0)}")
    _, _, vw, vh = map(float, view.replace(",", " ").split())
    if min(vw, vh) <= 0:
        raise ValueError("pictogram requires an SVG viewport")
    p = spec.get("padding", 20)
    w, h = width - 2 * p, height - 2 * p
    scale = min(w / vw, h / vh)
    ctx = surface.ctx
    surface.rect((0, 0, width, height), spec.get("background", "white"))
    # Preserve the registered tree for later specs with different data styles.
    root = deepcopy(root)
    names = {
        r[spec.get("nameField", "name")]
        for r in rows
        if spec.get("nameField", "name") in r
    }
    styles = spec.get("pictogram", {}).get("style", {})
    for node in root.iter():
        if node.get("name") in names:
            for attr, key in (
                ("fill", "fill"),
                ("stroke", "stroke"),
                ("stroke-width", "lineWidth"),
            ):
                if key in styles:
                    node.set(attr, str(styles[key]))
        # VChart 2.2.1 drops URL paint servers when converting SVG graphics.
        for attr in ("fill", "stroke"):
            if "url(" in node.get(attr, ""):
                node.set(attr, "none")
        for attr in node.attrib:
            if attr.split("}")[-1] == "href" and not node.attrib[attr].startswith(
                ("#", "data:")
            ):
                raise ValueError(
                    "pictogram requires local fragment references or embedded images"
                )
    root.attrib.setdefault("fill", spec.get("defaultFillColor", "black"))
    root.set("width", str(vw))
    root.set("height", str(vh))
    svg = skia.SVGDOM.MakeFromStream(skia.MemoryStream(ElementTree.tostring(root)))
    if svg is None:
        raise ValueError("Invalid pictogram SVG")
    tile = skia.Surface(width, height)
    canvas = tile.getCanvas()
    bg = ctx.getImageData(0, 0, width, height)
    pixels = np.frombuffer(bytes(bg.data), dtype=np.uint8).reshape(height, width, 4)
    canvas.drawImage(
        skia.Image.fromarray(pixels, colorType=skia.ColorType.kRGBA_8888_ColorType),
        0,
        0,
    )
    canvas.translate(p + (w - vw * scale) / 2, p + (h - vh * scale) / 2)
    canvas.scale(scale, scale)
    canvas.clipRect(skia.Rect.MakeWH(vw, vh))
    svg.render(canvas)
    output = tile.makeImageSnapshot().toarray(
        colorType=skia.ColorType.kRGBA_8888_ColorType
    )
    ctx.putImageData(ImageData(output.tobytes(), width, height), 0, 0)
    return dict(plot=[p, p, w, h], labels=[], axes=[], marks={})


def place_image(w, h, size, placed, step, padding):
    iw, ih = size
    # The native spiral is sampled in tenths of a radian. The filling pass
    # uses half steps, allowing smaller repeated images between primary ones.
    t = 0
    radius = hypot(w, h) / 2
    while t <= 2 * radius:
        x = int(w / 2 + (w / h) * t * cos(t) - iw / 2)
        y = int(h / 2 + t * sin(t) - ih / 2)
        if 0 <= x and x + iw < w and 0 <= y and y + ih < h:
            if all(
                x + iw + 2 * padding < a
                or y + ih + 2 * padding < b
                or x > a + c + 2 * padding
                or y > b + d + 2 * padding
                for a, b, c, d in placed
            ):
                return x, y, iw, ih
        t = round(t + 0.1 * step, 8)
    return None


def render_image_cloud(spec, surface, width, height):

    rows = records(
        spec,
        {
            "urlField",
            "nameField",
            "valueField",
            "imageSize",
            "layoutConfig",
            "image",
            "ratio",
        },
    )
    layout = spec.get("layoutConfig", {})
    check_keys(
        layout,
        {"layoutMode", "spiralType", "minFillingImageSize", "fillingTimes"},
        "imageCloud.layoutConfig",
    )
    if (
        layout.get("layoutMode", "spiral") != "spiral"
        or layout.get("spiralType", "archimedean") != "archimedean"
    ):
        raise ValueError("imageCloud supports the Archimedean spiral")
    p = spec.get("padding", 20)
    w, h = width - 2 * p, height - 2 * p
    spacing = spec.get("image", {}).get("padding", 0)
    images = []
    for row in sorted(
        rows, key=lambda r: r.get(spec.get("valueField"), 0), reverse=True
    ):
        uri = field(row, spec["urlField"])
        images.append(embedded_image(uri))
    surface.rect((0, 0, width, height), spec.get("background", "white"))
    placed, main = [], []
    if images:
        area = sum(min(im.width / im.height, im.height / im.width) for im in images)
        size = spec.get(
            "imageSize",
            max(1, int(sqrt(spec.get("ratio", 0.45) * w * h / area)) - 2 * spacing),
        )
        for repeat in range(1 + layout.get("fillingTimes", 4)):
            if repeat and not main:
                break
            for im in images:
                large = size
                if repeat:
                    axis = 2 if im.width > im.height else 3
                    large = max(
                        layout.get("minFillingImageSize", 10),
                        min(r[axis] for r in main) / 2 - repeat + 1,
                    )
                iw, ih = (
                    int(large * min(1, im.width / im.height)),
                    int(large * min(1, im.height / im.width)),
                )
                if min(iw, ih) <= 0:
                    raise ValueError("imageCloud requires positive image dimensions")
                box = place_image(w, h, (iw, ih), placed, 0.5 if repeat else 1, spacing)
                if box:
                    placed.append(box)
                    if not repeat:
                        main.append(box)
                    surface.ctx.drawImage(im, p + box[0], p + box[1], iw, ih)
    return dict(
        plot=[p, p, w, h],
        axes=[],
        labels=[],
        marks={"image": [[p + x, p + y, iw, ih] for x, y, iw, ih in placed]},
    )
