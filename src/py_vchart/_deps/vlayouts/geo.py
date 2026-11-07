"""Local-region Mercator paths for clockwise GeoJSON polygons."""

from math import asin, cos, hypot, isfinite, log, pi, radians, sin, tan, atan2



def _ring(raw, exterior):
    if not isinstance(raw, list) or len(raw) < 4 or raw[0] != raw[-1]:
        raise ValueError("map polygons require closed rings with at least three vertices")
    points = []
    for coord in raw[:-1]:
        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
            raise ValueError("map requires longitude/latitude positions")
        lon, lat = coord[:2]
        if not all(type(n) in (int, float) and isfinite(n) for n in (lon, lat)):
            raise ValueError("map requires finite coordinates")
        if abs(lon) > 180 or abs(lat) >= 85:
            raise ValueError("map supports local Mercator regions below 85 degrees latitude")
        points.append((radians(lon), radians(lat)))
    area = sum(a*d-b*c for (a,b),(c,d) in zip(points, points[1:] + points[:1]))
    if (area >= 0 if exterior else area <= 0):
        raise ValueError("map requires clockwise exterior rings and counterclockwise holes")
    return points


def read_features(source):
    if not isinstance(source, dict) or source.get("type") != "FeatureCollection" or not source.get("features"):
        raise ValueError("map requires a nonempty GeoJSON FeatureCollection")
    features = []
    for f in source["features"]:
        if not isinstance(f, dict) or f.get("type") != "Feature" or not isinstance(f.get("geometry"), dict):
            raise ValueError("map requires Feature geometries")
        geometry = f["geometry"]
        polygons = geometry.get("coordinates")
        if geometry.get("type") == "Polygon":
            polygons = [polygons]
        elif geometry.get("type") != "MultiPolygon":
            raise ValueError("map supports Polygon and MultiPolygon")
        if not isinstance(polygons, list) or not polygons or any(not isinstance(p, list) or not p for p in polygons):
            raise ValueError("map requires nonempty polygons")
        rings = [_ring(r, i == 0) for polygon in polygons for i, r in enumerate(polygon)]
        properties = f.get("properties") or {}
        if not isinstance(properties, dict):
            raise ValueError("map requires object properties")
        features.append((properties.copy(), rings))
    return features


def _mercator(point):
    lon, lat = point
    return lon, -log(tan(pi / 4 + lat / 2))


def _sample(ring, scale):
    # Subdivide a great-circle edge until its projected chord meets the
    # native half-square-pixel tolerance. The closing edge participates too.
    out = []
    def edge(a, b, depth):
        x, y = _mercator(a)
        u, v = _mercator(b)
        dx, dy = u-x, v-y
        length2 = dx*dx + dy*dy
        if depth == 0 or length2 * scale**2 <= 2:
            return
        ax, ay, az = cos(a[1])*cos(a[0]), cos(a[1])*sin(a[0]), sin(a[1])
        bx, by, bz = cos(b[1])*cos(b[0]), cos(b[1])*sin(b[0]), sin(b[1])
        sx, sy, sz = ax+bx, ay+by, az+bz
        mid = atan2(sy, sx), asin(sz/hypot(sx, sy, sz))
        mx, my = _mercator(mid)
        rx, ry = mx-x, my-y
        if ((dy*rx-dx*ry)**2 * scale**2 > 0.5*length2
                or abs((dx*rx+dy*ry)/length2 - 0.5) > 0.3
                or ax*bx+ay*by+az*bz < cos(pi/6)):
            edge(a, mid, depth-1)
            out.append((mx, my))
            edge(mid, b, depth-1)

    for i, a in enumerate(ring):
        out.append(_mercator(a))
        edge(a, ring[(i+1) % len(ring)], 16)
    return out


def fit_paths(features, plot):
    px, py, width, height = plot
    rings = [ring for _, feature in features for ring in feature]
    longitudes = [lon for ring in rings for lon, _ in ring]
    if max(longitudes)-min(longitudes) >= pi:
        raise ValueError("map requires a region spanning less than 180 degrees longitude")
    points = [p for ring in rings for p in _sample(ring, 150)]
    xs, ys = zip(*points)
    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    scale = min(width/(right-left), height/(bottom-top))
    tx = px + (width-scale*(right+left))/2
    ty = py + (height-scale*(bottom+top))/2
    return [[[[tx+x*scale, ty+y*scale] for x,y in _sample(ring, scale)] for ring in rings]
            for _, rings in features]
