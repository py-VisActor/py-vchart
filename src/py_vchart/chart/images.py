"""Static image marks, fitted SVG sources and image-cloud spiral packing."""

from math import cos, hypot, sin, sqrt
from xml.etree import ElementTree

from .._deps.vrender.images import embedded_image
from .cartesian import check_keys
from .layout_helpers import field, records

ElementTree.register_namespace("", "http://www.w3.org/2000/svg")
_svg_sources = {}


def register_svg_source(name, source):
    # Preserve the legacy registration/error boundary: URI validation occurs
    # before actual render/decode, not while storing a harmless XML tree.
    root = _parse_svg(source)
    if root.tag.split("}")[-1] != "svg":
        raise ValueError("pictogram source must be SVG")
    _svg_sources[name] = root


def _reference_pictogram(spec, surface, width, height):
    from copy import deepcopy

    import numpy as np
    import skia
    from py_skia_canvas import ImageData

    rows = records(
        spec, {"svg", "nameField", "valueField", "pictogram", "defaultFillColor"}
    )
    root = _registered_svg(spec["svg"])
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


def _parse_svg(source):
    import re
    if not isinstance(source,(str,bytes)) or len(source)>8_000_000:
        raise ValueError('SVG source must be bounded explicit text/bytes')
    text=source.decode('utf8') if isinstance(source,bytes) else source
    if re.search(r'<!DOCTYPE|<!ENTITY|@import',text,re.I):raise ValueError('External SVG declarations are forbidden')
    root=ElementTree.fromstring(text)
    if root.tag.split('}')[-1]!='svg':raise ValueError('pictogram source must be SVG')
    return root


def validate_svg(source,*,_depth=0):
    """Explicit offline SVG data only; never resolve URI/resource dependencies."""
    import re
    if _depth>8:raise ValueError('Nested SVG resource budget exceeded')
    root=_parse_svg(source)
    for node in root.iter():
        tag=node.tag.split('}')[-1].lower()
        if tag in ('script','foreignobject','iframe','audio','video'):
            raise ValueError('SVG host/executable content is forbidden')
        if tag=='style':
            for reference in re.findall(r'url\((.*?)\)',''.join(node.itertext()),re.I):
                if not reference.strip().strip('"\'').startswith('#'):
                    raise ValueError('External SVG style references are forbidden')
        for key,value in node.attrib.items():
            name=key.split('}')[-1].lower()
            if name.startswith('on'):raise ValueError('SVG event handlers are forbidden')
            if name=='href' and not value.startswith(('#','data:image/')):
                raise ValueError('SVG requires local fragment references or embedded images; explicit offline references only')
            if name=='href' and value.startswith('data:image/svg+xml'):
                import base64
                from urllib.parse import unquote_to_bytes
                header,body=value.split(',',1)
                nested=base64.b64decode(body,validate=True) if ';base64' in header else unquote_to_bytes(body)
                validate_svg(nested,_depth=_depth+1)
            if name in ('style','fill','stroke','filter','clip-path','mask','marker-start','marker-mid','marker-end','cursor') and 'url(' in value.lower():
                # Check each reference after stripping optional CSS quotation.
                for reference in re.findall(r'url\((.*?)\)',value,re.I):
                    if not reference.strip().strip('\"\'').startswith('#'):
                        raise ValueError('External SVG paint references are forbidden')
    return root


def _registered_svg(name):
    from .._deps.vrender._state import svg_sources
    sources=svg_sources.get()
    root=(_svg_sources if sources is None else sources).get(name)
    return None if root is None else validate_svg(ElementTree.tostring(root))


def render_pictogram(spec,surface,width,height):
    if surface.text_engine=='reference':return _reference_pictogram(spec,surface,width,height)
    from copy import deepcopy
    from py_skia_canvas import Image
    rows=records(spec,{'svg','nameField','valueField','pictogram','defaultFillColor'})
    stored=_registered_svg(spec['svg'])
    if stored is None:raise ValueError('Unregistered pictogram SVG: '+str(spec['svg']))
    root=deepcopy(stored)
    view=root.get('viewBox',f"0 0 {root.get('width',0)} {root.get('height',0)}")
    _,_,vw,vh=map(float,view.replace(',',' ').split())
    from math import isfinite
    if not all(isfinite(v) and v>0 for v in (vw,vh)):raise ValueError('pictogram requires an SVG viewport')
    p=spec.get('padding',20);w,h=width-2*p,height-2*p;scale=min(w/vw,h/vh)
    if min(w,h)<=0:raise ValueError('pictogram padding exceeds canvas')
    names={r[spec.get('nameField','name')] for r in rows if spec.get('nameField','name') in r}
    styles=spec.get('pictogram',{}).get('style',{})
    for node in root.iter():
        if node.get('name') in names:
            for attr,key in [('fill','fill'),('stroke','stroke'),('stroke-width','lineWidth')]:
                if key in styles:node.set(attr,str(styles[key]))
        for attr in ('fill','stroke'):
            if 'url(' in node.get(attr,''):node.set(attr,'none')
    root.attrib.setdefault('fill',spec.get('defaultFillColor','black'));root.set('width',str(vw));root.set('height',str(vh))
    image=Image(ElementTree.tostring(root))
    ctx=surface.ctx;ctx.save()
    try:
        surface.rect((0,0,width,height),spec.get('background','white'))
        ctx.translate(p+(w-vw*scale)/2,p+(h-vh*scale)/2);ctx.scale(scale,scale)
        ctx.beginPath();ctx.rect(0,0,vw,vh);ctx.clip();ctx.drawImage(image,0,0,vw,vh)
    finally:ctx.restore()
    return dict(plot=[p,p,w,h],labels=[],axes=[],marks={})
