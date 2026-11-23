"""Build the profile hero card in a dark and a light version.

The card is a terminal window. The left half is a short profile, the right
half is a small Enigma machine whose lamps spell out a word, a nod to the
"next codebreaker" motto. Everything is plain SVG with SMIL animation so it
plays inside GitHub's image proxy.

Run from the repository root:  python3 scripts/build_hero.py
"""

from pathlib import Path
import random

OUT = Path(__file__).resolve().parent.parent / "assets"

W, H = 850, 400
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

NAME = "Ayesha Irshad"
LAMP_WORD = "CODEBREAKER"
PROFILE = [
    ("role", "AI Engineer @ Ahoy"),
    ("also", "Solo founder, building on the side"),
    ("base", "Karachi, Pakistan"),
    ("focus", "Multi-agent systems, LLM tooling"),
    ("stack", "Python · TypeScript · LangGraph · Postgres"),
    ("now", "Codet.ai · DiffSpy · NEXUS"),
]
MOTTO = ("I may not be Alan Turing, but I am confident", "enough to be the next codebreaker.")

THEMES = {
    "dark": dict(
        bg="#0a0e17", bar="#0f1525", border="#1a2340", panel="#111827",
        text="#c9d1d9", muted="#6b7a99", faint="#3d4f6f",
        green="#00ff9f", purple="#7b61ff", pink="#ff6ac1",
        lamp_off="#161d2f", lamp_on="#ffbd2e", lamp_text_off="#3d4f6f", lamp_text_on="#0a0e17",
    ),
    "light": dict(
        bg="#f6f8fa", bar="#eaeef2", border="#d0d7de", panel="#ffffff",
        text="#1f2328", muted="#57606a", faint="#8c959f",
        green="#0a7d55", purple="#5b3fd6", pink="#b8327f",
        lamp_off="#eaeef2", lamp_on="#d4a017", lamp_text_off="#8c959f", lamp_text_on="#ffffff",
    ),
}

KEYBOARD = ["QWERTZUIO", "ASDFGHJK", "PYXCVBNML"]  # the real Enigma lamp layout


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, fill, size=13, weight=None, anchor=None, extra=""):
    attrs = f'x="{x}" y="{y}" fill="{fill}" font-size="{size}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f'<text {attrs}{extra}>{esc(s)}</text>'


def decrypt_frames(target, steps=9, seed=7):
    """Frames that turn random capitals into the target, left to right."""
    rnd = random.Random(seed)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    frames = []
    for step in range(steps):
        solved = round(len(target) * step / (steps - 1))
        frame = "".join(
            ch if (i < solved or ch == " ") else rnd.choice(letters)
            for i, ch in enumerate(target)
        )
        frames.append(frame)
    return frames


def name_block(t, x, y):
    """The name types itself out of ciphertext once, then stays."""
    frames = decrypt_frames(NAME)
    step = 0.12
    start = 0.0
    out = []
    for i, frame in enumerate(frames):
        last = i == len(frames) - 1
        begin = start + i * step
        if last:
            # Visible by default, hidden only while the cipher frames play, so
            # a viewer without animation support still shows the name.
            out.append(
                f'<text x="{x}" y="{y}" fill="{t["green"]}" font-size="26" font-weight="700">{esc(frame)}'
                f'<set attributeName="opacity" to="0" begin="0s" end="{begin:.2f}s"/></text>'
            )
        else:
            out.append(
                f'<text x="{x}" y="{y}" fill="{t["purple"]}" font-size="26" font-weight="700" opacity="0">{esc(frame)}'
                f'<set attributeName="opacity" to="1" begin="{begin:.2f}s" end="{begin + step:.2f}s"/></text>'
            )
    return "\n".join(out)


def lamps(t, cx0, cy0):
    """Lamp board. Lamps light one by one to spell LAMP_WORD, then rest."""
    slots = len(LAMP_WORD) + 4  # four dark slots before the loop restarts
    slot_time = 0.55
    dur = slots * slot_time
    key_times = ";".join(f"{i / slots:.4f}" for i in range(slots)) + ";1"

    r, gap = 13, 34
    out = []
    for row_i, row in enumerate(KEYBOARD):
        row_x = cx0 + (len(KEYBOARD[0]) - len(row)) * gap / 2
        for col_i, ch in enumerate(row):
            cx = row_x + col_i * gap
            cy = cy0 + row_i * 38
            lit = [1 if i < len(LAMP_WORD) and LAMP_WORD[i] == ch else 0 for i in range(slots)]
            out.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="{t["lamp_off"]}" stroke="{t["border"]}"/>')
            out.append(text(f"{cx:.1f}", cy + 4.5, ch, t["lamp_text_off"], size=12, anchor="middle"))
            if any(lit):
                values = ";".join(str(v) for v in lit + [lit[0]])
                anim = (f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
                        f'dur="{dur:.2f}s" calcMode="discrete" repeatCount="indefinite"/>')
                out.append(
                    f'<g opacity="0">{anim}'
                    f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="{t["lamp_on"]}"/>'
                    + text(f"{cx:.1f}", cy + 4.5, ch, t["lamp_text_on"], size=12, weight="700", anchor="middle")
                    + "</g>"
                )
    return "\n".join(out), slots, slot_time


def rotors(t, x0, y0, slots, slot_time):
    """Three rotor windows. The right rotor steps on every key, like the real one."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    dur = slots * slot_time
    win_w, win_h, gap = 46, 30, 18
    out = [f'<clipPath id="rw"><rect x="0" y="0" width="{win_w}" height="{win_h}" rx="5"/></clipPath>']
    starts = (0, 4, 19)  # A, E, T
    steps_per_key = (0, 0, 1)
    for i, (start, step) in enumerate(zip(starts, steps_per_key)):
        x = x0 + i * (win_w + gap)
        out.append(f'<g transform="translate({x},{y0})">')
        out.append(f'<rect width="{win_w}" height="{win_h}" rx="5" fill="{t["panel"]}" stroke="{t["border"]}"/>')
        out.append('<g clip-path="url(#rw)">')
        # a vertical strip of letters that slides up one letter per key press
        strip = []
        for j in range(len(alphabet) + slots + 1):
            ch = alphabet[(start + j) % 26]
            strip.append(text(win_w / 2, 20 + j * win_h, ch, t["text"], size=15, weight="700", anchor="middle"))
        if step:
            pressed = len(LAMP_WORD)
            values = []
            for s in range(slots + 1):
                values.append(f"0 {-min(s, pressed) * win_h}")
            values[-1] = "0 0"
            key_times = ";".join(f"{s / slots:.4f}" for s in range(slots)) + ";1"
            anim = (f'<animateTransform attributeName="transform" type="translate" values="{";".join(values)}" '
                    f'keyTimes="{key_times}" dur="{dur:.2f}s" calcMode="discrete" repeatCount="indefinite"/>')
            out.append(f"<g>{anim}{''.join(strip)}</g>")
        else:
            out.append("".join(strip[:1]))
        out.append("</g>")
        out.append(text(win_w / 2, win_h + 16, ["I", "II", "III"][i], t["faint"], size=10, anchor="middle"))
        out.append("</g>")
    return "\n".join(out)


def build(theme):
    t = THEMES[theme]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" aria-label="Ayesha Irshad, AI engineer and founder">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}"/>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}"/>',
        # title bar
        f'<path d="M0.5 32V10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10V32z" fill="{t["bar"]}"/>',
        f'<line x1="0" y1="32.5" x2="{W}" y2="32.5" stroke="{t["border"]}"/>',
        f'<circle cx="18" cy="16" r="5.5" fill="#ff5f56"/>',
        f'<circle cx="36" cy="16" r="5.5" fill="#ffbd2e"/>',
        f'<circle cx="54" cy="16" r="5.5" fill="#27c93f"/>',
        text(W / 2, 20, "ayesha@codebreaker: ~", t["faint"], size=11.5, anchor="middle"),
    ]

    # left column: profile
    x = 28
    parts.append(text(x, 64, "❯", t["purple"], weight="700"))
    parts.append(text(x + 18, 64, "whoami", t["green"]))
    parts.append(name_block(t, x, 102))
    parts.append(f'<line x1="{x}" y1="118" x2="{x + 400}" y2="118" stroke="{t["border"]}" stroke-dasharray="3 5"/>')
    y = 144
    for key, value in PROFILE:
        parts.append(text(x, y, key, t["pink"], size=12.5))
        parts.append(text(x + 70, y, value, t["text"], size=12.5))
        y += 24
    y += 14
    parts.append(text(x, y, "❯", t["purple"], weight="700"))
    parts.append(text(x + 18, y, "cat motto.txt", t["green"]))
    parts.append(text(x, y + 26, MOTTO[0], t["muted"], size=12, extra=' font-style="italic"'))
    parts.append(text(x, y + 44, MOTTO[1], t["muted"], size=12, extra=' font-style="italic"'))
    cursor_x = x + len(MOTTO[1]) * 7.25 + 6
    parts.append(
        f'<rect x="{cursor_x:.1f}" y="{y + 33}" width="7" height="14" fill="{t["green"]}">'
        '<animate attributeName="opacity" values="1;0;1" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/>'
        "</rect>"
    )

    # right column: the machine
    mx, my, mw, mh = 488, 52, 340, 330
    parts.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="10" fill="{t["panel"]}" stroke="{t["border"]}"/>')
    parts.append(text(mx + 18, my + 26, "enigma --rotors I,II,III", t["faint"], size=11))
    lamp_svg, slots, slot_time = lamps(t, mx + 34, my + 168)
    parts.append(rotors(t, mx + (mw - 174) / 2, my + 50, slots, slot_time))
    parts.append(f'<line x1="{mx + 18}" y1="{my + 128}" x2="{mx + mw - 18}" y2="{my + 128}" stroke="{t["border"]}"/>')
    parts.append(lamp_svg)
    parts.append(text(mx + mw / 2, my + mh - 18, "the lamps spell what I like doing", t["faint"], size=10.5, anchor="middle"))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        path = OUT / f"hero-{theme}.svg"
        path.write_text(build(theme), encoding="utf-8")
        print("wrote", path.relative_to(OUT.parent))


if __name__ == "__main__":
    main()
