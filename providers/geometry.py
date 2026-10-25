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
