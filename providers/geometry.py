"""Border shapes made small enough for a world map. Shared by every provider that loads shapes."""

import math


def simplify(geometry, tolerance, decimals):
    """A GeoJSON Polygon or MultiPolygon as a simplified MultiPolygon.

    `tolerance` and the rounding to `decimals` are in degrees.
    """
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    kept = []
    for polygon in polygons:
        rings = [_simplify_ring(ring, tolerance, decimals) for ring in polygon]
        # A polygon whose outer ring collapsed is an islet too small to see: drop it.
        if rings[0]:
            kept.append([ring for ring in rings if ring])
    if not kept:
        # Keep the largest original polygon so tiny countries still show up.
        largest = max(polygons, key=lambda poly: len(poly[0]))
        kept = [[[[round(x, decimals), round(y, decimals)] for x, y in largest[0]]]]
    return {'type': 'MultiPolygon', 'coordinates': kept}


def moved(geometry, scale, centre):
    """The geometry scaled by `scale` around its own centre and moved to `centre` (lon, lat): an inset of a far-off
    part beside the mainland, as atlases draw Alaska or the French overseas départements.
    Longitudes east of 180° are taken west of it first, so a shape across the antimeridian stays whole.
    """
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    points = [(x - 360 if x > 0 else x, y) for polygon in polygons for ring in polygon for x, y in ring]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    nx, ny = centre

    def move(ring):
        return [[round(nx + ((x - 360 if x > 0 else x) - cx) * scale, 4), round(ny + (y - cy) * scale, 4)] for x, y in ring]
    return {'type': 'MultiPolygon', 'coordinates': [[move(ring) for ring in polygon] for polygon in polygons]}


def dissolve(geometries):
    """One MultiPolygon from neighbouring MultiPolygons that share their borders point for point, as Natural Earth's units
    of one country do: the shared edges are dropped and the rest chained into rings. Holes are not kept.
    """
    edges = {}
    for geometry in geometries:
        for polygon in geometry['coordinates']:
            ring = polygon[0]
            for a, b in zip(ring, ring[1:]):
                a, b = tuple(a), tuple(b)
                if a == b:
                    continue
                key = (a, b) if a <= b else (b, a)
                edges[key] = edges.get(key, 0) + 1
    outer = [edge for edge, count in edges.items() if count == 1]
    following = {}
    for a, b in outer:
        following.setdefault(a, []).append(b)
        following.setdefault(b, []).append(a)
    rings = []
    seen = set()
    for start in following:
        if start in seen:
            continue
        ring, point = [start], start
        seen.add(start)
        while True:
            step = next((other for other in following[point] if other not in seen), None)
            if step is None:
                break
            seen.add(step)
            ring.append(step)
            point = step
        if len(ring) >= 3:
            rings.append([[list(point) for point in ring] + [list(ring[0])]])
    return {'type': 'MultiPolygon', 'coordinates': rings}


def _simplify_ring(ring, tolerance, decimals):
    points = douglas_peucker(ring, tolerance)
    rounded = []
    for x, y in points:
        point = [round(x, decimals), round(y, decimals)]
        if not rounded or point != rounded[-1]:
            rounded.append(point)
    # A ring needs at least 3 distinct corners plus the closing point.
    return rounded if len(rounded) >= 4 else None


def douglas_peucker(points, tolerance):
    """Drop points that sit within `tolerance` of the line between their kept neighbours."""
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        (x1, y1), (x2, y2) = points[start][:2], points[end][:2]
        length = math.hypot(x2 - x1, y2 - y1)
        farthest, index = 0.0, None
        for i in range(start + 1, end):
            x0, y0 = points[i][:2]
            if length:
                distance = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / length
            else:
                distance = math.hypot(x0 - x1, y0 - y1)
            if distance > farthest:
                farthest, index = distance, i
        if index is not None and farthest > tolerance:
            keep[index] = True
            stack.extend([(start, index), (index, end)])
    return [point for point, kept in zip(points, keep) if kept]
