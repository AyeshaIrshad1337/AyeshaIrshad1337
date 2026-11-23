"""An original rubber duck, drawn as coloured ASCII art and animated in SVG.

The duck is the programmer's debugging duck: you explain the bug to it and the
answer turns up. It is built from a few simple shapes, shaded from the top
left, then:

- decodes out of scrambled characters when the page loads,
- bobs on the water,
- blinks now and then,
- has question marks float up while it "thinks",
- cycles through a short caption.

Everything is plain SVG with SMIL, so it plays inside GitHub's image proxy.
"""

import math
import random

COLS, ROWS = 54, 26
CW, CH = 5.4, 9.6        # character cell size at font size 9
FONT_SIZE = 9
WATER_ROW = 22           # first row of water
Y_SHIFT = 40             # the shapes below are drawn this far down; skip the empty top

COLORS = {
    "dark": dict(hi="#ffe58f", mid="#f2c12e", lo="#c9940a", edge="#8f6a07",
                 beak="#f0883e", beak_lo="#bd561d", eye="#0d1117", water="#58a6ff", foam="#a5d6ff"),
    "light": dict(hi="#f5c518", mid="#e0a800", lo="#b07d00", edge="#7a5600",
                  beak="#e36d0a", beak_lo="#a8470a", eye="#1f2328", water="#0969da", foam="#54aeff"),
}


def _ellipse(px, py, cx, cy, rx, ry):
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2


def _shade(px, py, cx, cy, rx, ry):
    """Positive towards the top left (lit), negative towards the bottom right."""
    return -0.55 * (px - cx) / rx - 0.85 * (py - cy) / ry


def draw():
    """Return a grid of (char, colour key) or None, plus the eye cells."""
    head = (110, 98, 52, 50)
    body = (168, 196, 108, 62)
    tail = (258, 150, 30, 34)
    beak_top = (46, 108, 34, 13)
    beak_low = (54, 122, 26, 8)
    wing = (186, 192, 58, 32)
    eye = (96, 84, 7, 8)

    grid = [[None] * COLS for _ in range(ROWS)]
    eye_cells = []
    for r in range(ROWS):
        for c in range(COLS):
            px, py = c * CW + CW / 2, r * CH + CH / 2 + Y_SHIFT
            cell = None
            if _ellipse(px, py, *eye) <= 1:
                cell = ("@", "eye")
                eye_cells.append((c, r))
            elif _ellipse(px, py, *beak_low) <= 1:
                cell = ("#", "beak_lo")
            elif _ellipse(px, py, *beak_top) <= 1:
                cell = ("%" if _shade(px, py, *beak_top) > -0.2 else "#", "beak")
            else:
                for shape in (head, body, tail):
                    d = _ellipse(px, py, *shape)
                    if d <= 1:
                        s = _shade(px, py, *shape)
                        if d > 0.88:
                            cell = ("@", "edge")
                        elif s > 0.45:
                            cell = ("*", "hi")
                        elif s < -0.35:
                            cell = ("#", "lo")
                        else:
                            cell = ("%", "mid")
                        if shape is body and 0.7 < _ellipse(px, py, *wing) <= 1 and py > wing[1] - 10:
                            cell = ("#", "lo")
                        break
            if r >= WATER_ROW:
                cell = None
            grid[r][c] = cell
    return grid, eye_cells


def _row_text(r, cells, x0, y0, fill_of):
    """One row as a <text> with a positioned <tspan> per run of one colour."""
    spans, run_start, run_key, run_chars = [], None, None, []

    def flush():
        if run_chars:
            # one x per character keeps the grid exact whatever font the viewer has
            xs = " ".join(f"{x0 + (run_start + i) * CW:.1f}" for i in range(len(run_chars)))
            spans.append(f'<tspan x="{xs}" fill="{fill_of(run_key)}">{"".join(run_chars)}</tspan>')

    for c, cell in enumerate(cells):
        key = cell[1] if cell else None
        if key != run_key or cell is None:
            flush()
            run_chars = []
            run_start, run_key = c, key
        if cell:
            run_chars.append(cell[0].replace("&", "&amp;").replace("<", "&lt;"))
    flush()
    if not spans:
        return ""
    return f'<text y="{y0 + r * CH + CH - 2:.1f}">{"".join(spans)}</text>'


def duck_svg(x0, y0, theme, muted, faint, clip_id="duck"):
    k = COLORS[theme]
    grid, eye_cells = draw()
    width, height = COLS * CW, ROWS * CH
    rnd = random.Random(11)
    decode = 1.4  # seconds to decode
    out = [f'<g font-size="{FONT_SIZE}" font-weight="700">']

    # clip paths: the duck is revealed top to bottom, the scramble goes away with it
    out.append(
        f'<clipPath id="{clip_id}-shown"><rect x="{x0}" y="{y0}" width="{width}" height="{height}">'
        f'<animate attributeName="height" values="0;{height}" dur="{decode}s" fill="freeze"/></rect></clipPath>'
        f'<clipPath id="{clip_id}-noise"><rect x="{x0}" y="{y0 + height}" width="{width}" height="{height}">'
        f'<animate attributeName="y" values="{y0};{y0 + height}" dur="{decode}s" fill="freeze"/></rect></clipPath>'
    )

    # scrambled characters in the duck's outline, flickering between three frames
    noise_chars = "ABCDEF0123456789#%&*+=?/"
    out.append(f'<g clip-path="url(#{clip_id}-noise)">')
    for f in range(3):
        values = ";".join("1" if i == f else "0" for i in range(3)) + f";{'1' if f == 0 else '0'}"
        out.append(f'<g opacity="{1 if f == 0 else 0}"><animate attributeName="opacity" values="{values}" '
                   f'keyTimes="0;0.33;0.66;1" dur="0.3s" calcMode="discrete" repeatCount="5"/>')
        for r in range(ROWS):
            noisy = [(rnd.choice(noise_chars), "n") if grid[r][c] else None for c in range(COLS)]
            out.append(_row_text(r, noisy, x0, y0, lambda _: faint))
        out.append("</g>")
    out.append("</g>")

    # the duck itself, bobbing gently once it has decoded
    out.append(f'<g clip-path="url(#{clip_id}-shown)"><g>')
    out.append(f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" '
               f'dur="2.8s" begin="{decode}s" repeatCount="indefinite"/>')
    for r in range(ROWS):
        out.append(_row_text(r, grid[r], x0, y0, lambda key: k[key]))

    # blink: cover the eye with body colour for a moment every few seconds
    blink = "".join(
        f'<text x="{x0 + c * CW:.1f}" y="{y0 + r * CH + CH - 2:.1f}" fill="{k["mid"]}">%</text>' for c, r in eye_cells
    )
    out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="0;0.02;0.06;1" '
               f'dur="4.5s" begin="{decode + 1}s" calcMode="discrete" repeatCount="indefinite"/>{blink}</g>')

    # question marks drifting up from the head while the duck thinks
    for i, (dx, delay) in enumerate(((150, 0.0), (172, 1.0), (136, 2.0))):
        qx, qy = x0 + dx, y0 + 4
        out.append(
            f'<text x="{qx}" y="{qy}" fill="{k["mid"]}" font-size="14" font-weight="700" opacity="0">?'
            f'<animate attributeName="opacity" values="0;1;0" dur="3s" begin="{decode + delay}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{qy};{qy - 26}" dur="3s" begin="{decode + delay}s" repeatCount="indefinite"/>'
            "</text>"
        )
    out.append("</g></g>")

    # water, drifting slowly sideways
    wave = "~-~" * (COLS // 3 + 4)
    for i, color in enumerate((k["water"], k["foam"])):
        wy = y0 + (WATER_ROW + i) * CH + CH - 2
        out.append(f'<clipPath id="{clip_id}-water{i}"><rect x="{x0}" y="{wy - CH}" width="{width}" height="{CH + 2}"/></clipPath>')
        out.append(f'<g clip-path="url(#{clip_id}-water{i})"><text x="{x0 - 3 * CW * (i + 1):.1f}" y="{wy:.1f}" fill="{color}">{wave}'
                   f'<animateTransform attributeName="transform" type="translate" values="0 0;{3 * CW * (1 if i == 0 else -1):.1f} 0;0 0" '
                   f'dur="{4 + i}s" repeatCount="indefinite"/></text></g>')

    # captions: the rubber duck debugging story, one line at a time
    captions = ["explaining the bug to the duck...", "the duck is thinking", "oh. found it."]
    cy = y0 + height + 22
    for i, line in enumerate(captions):
        values = ";".join("1" if j == i else "0" for j in range(3)) + f";{'1' if i == 0 else '0'}"
        out.append(f'<text x="{x0 + width / 2:.1f}" y="{cy:.1f}" fill="{muted}" font-size="11" font-weight="400" text-anchor="middle" '
                   f'opacity="{1 if i == 0 else 0}">{line}'
                   f'<animate attributeName="opacity" values="{values}" keyTimes="0;0.33;0.66;1" dur="9s" '
                   f'calcMode="discrete" repeatCount="indefinite"/></text>')

    out.append("</g>")
    return "\n".join(out)


if __name__ == "__main__":
    grid, eyes = draw()
    for row in grid:
        print("".join(c[0] if c else " " for c in row))
