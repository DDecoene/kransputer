"""Pure geometry and grouping helpers for place.py. No pcbnew import here."""
import re


def grid_positions(n, cols, pitch_x_mm, pitch_y_mm, origin_mm):
    """Row-major (x, y) list for `n` items on a `cols`-wide grid."""
    ox, oy = origin_mm
    out = []
    for i in range(n):
        row, col = divmod(i, cols)
        out.append((ox + col * pitch_x_mm, oy + row * pitch_y_mm))
    return out


def bus_row_ys(row_spacing_mm, origin_y):
    """Y of the two edge-header rows."""
    return (origin_y, origin_y + row_spacing_mm)


def header_pin_xs(count, pitch_mm, origin_x):
    """X of each header pin, pin 1 at origin_x."""
    return [origin_x + i * pitch_mm for i in range(count)]


def outline_rect(points, margin_mm):
    """(x_min, y_min, x_max, y_max) bounding box of `points`, grown by margin."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs) - margin_mm, min(ys) - margin_mm,
            max(xs) + margin_mm, max(ys) + margin_mm)


def natural_key(ref):
    """Sort key so Q2 precedes Q10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def group_by_sheet(pairs):
    """[(ref, sheetname)] -> {sheetname or 'root': [ref, ...]} preserving order."""
    groups = {}
    for ref, sheet in pairs:
        groups.setdefault(sheet or "root", []).append(ref)
    return groups
