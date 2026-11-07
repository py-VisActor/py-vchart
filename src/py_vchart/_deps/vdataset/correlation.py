"""Map records to correlation symbols in region-local coordinates."""

from math import ceil, cos, pi, sin


def angle_sequence(start, end):
    slots = max(2, ceil(2*(end-start)/pi))
    step = (end-start)/slots
    origin, offset, direction = start, step/2, 1
    generation = 0
    while True:
        for i in range(slots):
            index = i//2 + (slots//2 if i % 2 else 0)
            yield origin + index*step*direction
        generation += 1
        direction = -direction
        origin = end-offset if direction < 0 else start+offset
        offset /= 2
        if generation >= 2:
            slots *= 2
            step /= 2


def map_values(values, limits, constant):
    low, high = min(values), max(values)
    if low == high:
        return [constant]*len(values)
    a, b = limits
    return [a + (b-a)*(v-low)/(high-low) for v in values]


def positions(values, sizes, radii, size_range, angles, center, bounds, obstacles):
    if not values:
        return []
    distances = map_values(values, radii, sum(radii)/2)
    diameters = map_values(sizes, size_range, size_range[1])
    start, end = sorted(angles)
    cx, cy = center
    width, height = bounds
    step = (end-start)/60
    result = []
    blockers = []
    for angle, distance, size, obstacle in zip(angle_sequence(start, end), distances, diameters, obstacles):
        for _ in range(60):
            x, y = cx+distance*cos(angle), cy+distance*sin(angle)
            inside = size <= x <= width-size and size <= y <= height-size
            if inside and not any((x-ox)**2+(y-oy)**2 < (size+r)**2 for ox, oy, r in blockers):
                break
            angle += step
            if angle > end:
                angle = start
        result.append((x, y, size))
        # The upstream transform checks the original x/y/size fields on prior records.
        if obstacle is not None:
            blockers.append(obstacle)
    return result
