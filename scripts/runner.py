"""An original little runner, drawn as coloured ASCII art and animated in SVG.

A round green character with a headband and amber sneakers. On a loop it
dashes in with speed lines behind it, skids to a stop in a puff of dust,
taps its foot and blinks, then dashes off again.

Everything is plain SVG with SMIL, so it plays inside GitHub's image proxy.
Without animation support the runner simply stands in the middle.
"""

import math

CW, CH = 5.4, 9.6        # character cell size at font size 9
FONT_SIZE = 9
COLS, ROWS = 40, 16
SCALE = 1.35             # grid cells per drawing unit, so the shapes come out bigger
Y_SHIFT = 24             # shapes are drawn this far down; skip the empty top
SLOT = 0.1               # seconds per animation step
SLOTS = 64               # one loop

COLORS = {
    "dark": dict(hi="#7ee787", mid="#3fb950", lo="#238636", edge="#196c2e", face="#f0e6d2",
                 eye="#0d1117", white="#e6edf3", shoe="#e3b341", shoe_lo="#bb8009",
                 speed="#6e7681", dust="#8b949e", ground="#30363d"),
    "light": dict(hi="#4ac26b", mid="#2da44e", lo="#1a7f37", edge="#116329", face="#f5e6c8",
                  eye="#1f2328", white="#ffffff", shoe="#d4a72c", shoe_lo="#9a6700",
                  speed="#8c959f", dust="#818b98", ground="#d0d7de"),
}

# ------------------------------------------------------------------ drawing


def _ell(px, py, cx, cy, rx, ry):
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2


def _seg(px, py, x1, y1, x2, y2):
    """Distance from a point to a line segment."""
    dx, dy = x2 - x1, y2 - y1
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


POSES = {
    # (front leg end, back leg end, front arm end, back arm end, headband tails flying?)
    "run_a": ((108, 124), (38, 118), (128, 70), (22, 84), True),
    "run_b": ((90, 128), (60, 124), (110, 86), (36, 70), True),
    "stand": ((86, 128), (58, 128), (116, 92), (30, 92), False),
    "tap":   ((94, 121), (58, 128), (116, 92), (30, 92), False),
}


def draw(pose, eyes_open=True):
    front, back, arm_f, arm_b, flying = POSES[pose]
    body = (72, 66, 40, 38)
    face = (86, 72, 22, 20)
    eyes = [(80, 60, 5, 6), (96, 60, 5, 6)]
    sclera = [(80, 60, 8, 9), (96, 60, 8, 9)]
    grid = [[None] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            px, py = (c * CW + CW / 2) / SCALE, (r * CH + CH / 2) / SCALE + Y_SHIFT
            cell = None
            # shoes first so they sit over the legs
            for (fx, fy) in (front, back):
                if _ell(px, py, fx + 6, fy, 13, 6) <= 1:
                    cell = ("#", "shoe_lo") if py > fy + 1 else ("%", "shoe")
            if cell is None:
                for (lx, ly), hip in ((front, (84, 98)), (back, (62, 98))):
                    if _seg(px, py, *hip, lx, ly) < 4.5:
                        cell = ("|", "lo")
                for (ax, ay), sh in ((arm_f, (104, 74)), (arm_b, (40, 74))):
                    if _seg(px, py, *sh, ax, ay) < 3.5:
                        cell = ("=", "lo")
            d = _ell(px, py, *body)
            if d <= 1:
                if eyes_open and any(_ell(px, py, *e) <= 1 for e in eyes):
                    cell = ("@", "eye")
                elif any(_ell(px, py, *s) <= 1 for s in sclera):
                    cell = ("-", "eye") if not eyes_open and abs(py - 60) < 5 else ("o", "white")
                elif 42 <= py <= 49:
                    cell = ("=", "white")          # headband
                elif _ell(px, py, *face) <= 1:
                    cell = (":", "face")
                elif d > 0.86:
                    cell = ("@", "edge")
                else:
                    s = -0.55 * (px - body[0]) / body[2] - 0.85 * (py - body[1]) / body[3]
                    cell = ("*", "hi") if s > 0.45 else ("#", "lo") if s < -0.35 else ("%", "mid")
            elif cell is None:
                # headband tails behind the head
                if flying and (_seg(px, py, 34, 45, 6, 37) < 2.5 or _seg(px, py, 34, 47, 4, 53) < 2.5):
                    cell = ("~", "white")
                if not flying and _seg(px, py, 33, 47, 26, 64) < 2.5:
                    cell = ("\\", "white")
            grid[r][c] = cell
    return grid


# ------------------------------------------------------------------ svg


def _row_text(r, cells, x0, y0, fill_of):
    spans, start, key, chars = [], None, None, []

    def flush():
        if chars:
            # one x per character keeps the grid exact whatever font the viewer has
            xs = " ".join(f"{x0 + (start + i) * CW:.1f}" for i in range(len(chars)))
            text = "".join(chars).replace("&", "&amp;").replace("<", "&lt;")
            spans.append(f'<tspan x="{xs}" fill="{fill_of(key)}">{text}</tspan>')

    for c, cell in enumerate(cells):
        k = cell[1] if cell else None
        if k != key or cell is None:
            flush()
            chars, start, key = [], c, k
        if cell:
            chars.append(cell[0])
    flush()
    return f'<text y="{y0 + r * CH + CH - 2:.1f}">{"".join(spans)}</text>' if spans else ""


def _grid_svg(grid, x0, y0, colors):
    return "".join(_row_text(r, row, x0, y0, lambda k: colors[k]) for r, row in enumerate(grid))


def _timeline():
    """What the runner does in each slot: (pose, eyes_open, x offset, speed lines, dust)."""
    plan = []
    for s in range(SLOTS):
        if s < 8:                                   # dash in
            pose, x, lines, dust = ("run_a", "run_b")[s % 2], -230 + s * 26, True, False
        elif s < 12:                                # skid
            pose, x, lines, dust = "run_b", -22 + (s - 8) * 6, False, True
        elif s < 50:                                # wait, tap foot, blink
            pose = "tap" if (s // 3) % 2 and 20 <= s < 40 else "stand"
            x, lines, dust = 0, False, s < 14
        else:                                       # dash off
            pose, x, lines, dust = ("run_a", "run_b")[s % 2], (s - 49) * 30, True, False
        eyes = not (s in (26, 27, 44))
        plan.append((pose, eyes, x, lines, dust))
    return plan


def _discrete(values):
    """An opacity animation that follows one value per slot and loops."""
    key_times = ";".join(f"{i / SLOTS:.4f}" for i in range(SLOTS)) + ";1"
    vals = ";".join(values + [values[0]])
    return (f'<animate attributeName="opacity" values="{vals}" keyTimes="{key_times}" '
            f'dur="{SLOTS * SLOT:.1f}s" calcMode="discrete" repeatCount="indefinite"/>')


def runner_svg(x0, y0, width, theme, muted, clip_id="run"):
    k = COLORS[theme]
    plan = _timeline()
    char_w, char_h = COLS * CW, ROWS * CH
    cx = x0 + (width - char_w) / 2           # where the runner stands
    ground_y = y0 + char_h - 2

    out = [f'<g font-size="{FONT_SIZE}" font-weight="700">',
           f'<clipPath id="{clip_id}"><rect x="{x0}" y="{y0 - 30}" width="{width}" height="{char_h + 60}"/></clipPath>',
           f'<line x1="{x0}" y1="{ground_y}" x2="{x0 + width}" y2="{ground_y}" stroke="{k["ground"]}" stroke-dasharray="2 4"/>',
           f'<g clip-path="url(#{clip_id})">']

    # dust puffs at the skid, left behind on the ground
    dust = "".join(f'<text x="{cx + dx:.1f}" y="{ground_y - 2 + dy}" fill="{k["dust"]}">{ch}</text>'
                   for dx, dy, ch in ((-6, 0, "o"), (-16, -6, "."), (-26, -2, "o"), (-34, -9, "."), (-12, -12, "°")))
    out.append(f'<g opacity="0">{_discrete(["1" if p[4] else "0" for p in plan])}{dust}</g>')

    # the moving runner: a horizontal slide with frames swapped underneath
    xs = [p[2] for p in plan]
    key_times = ";".join(f"{i / SLOTS:.4f}" for i in range(SLOTS)) + ";1"
    out.append(f'<g><animateTransform attributeName="transform" type="translate" '
               f'values="{";".join(f"{x} 0" for x in xs + [xs[0]])}" keyTimes="{key_times}" '
               f'dur="{SLOTS * SLOT:.1f}s" calcMode="discrete" repeatCount="indefinite"/>')

    # speed lines trail behind while running
    lines = "".join(f'<text x="{cx - 40 + off:.1f}" y="{y0 + row * CH:.1f}" fill="{k["speed"]}">{s}</text>'
                    for off, row, s in ((0, 4, "= =="), (-14, 7, "== = =="), (4, 10, "= =="), (-8, 13, "== =")))
    out.append(f'<g opacity="0">{_discrete(["1" if p[3] else "0" for p in plan])}{lines}</g>')

    frames = {}
    for pose, eyes, *_ in plan:
        frames.setdefault((pose, eyes), None)
    for (pose, eyes) in frames:
        shown = ["1" if (p[0], p[1]) == (pose, eyes) else "0" for p in plan]
        base = "1" if (pose, eyes) == ("stand", True) else "0"  # the still image without animation
        out.append(f'<g opacity="{base}">{_discrete(shown)}{_grid_svg(draw(pose, eyes), cx, y0, k)}</g>')
    out.append("</g></g>")

    out.append(f'<text x="{x0 + width / 2:.1f}" y="{ground_y + 30:.1f}" fill="{muted}" font-size="11" '
               f'font-weight="400" text-anchor="middle">shipping fast, fixing faster</text>')
    out.append("</g>")
    return "\n".join(out)


if __name__ == "__main__":
    for pose in POSES:
        print(pose)
        for row in draw(pose):
            print("".join(c[0] if c else " " for c in row))
