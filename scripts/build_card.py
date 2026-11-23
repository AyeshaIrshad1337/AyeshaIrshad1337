"""Build the profile card, in a dark and a light version.

One card holds the whole profile: who I am, what I am building, live GitHub
numbers and the motto on the left, and a small Enigma machine on the right
whose lamps spell out a word. It is plain SVG with SMIL animation, so it plays
inside GitHub's image proxy.

The GitHub numbers come from the API, so it needs a token in GITHUB_TOKEN
(the workflow's own token is enough). Only the standard library is used.

Run from the repository root:  GITHUB_TOKEN=... python3 scripts/build_card.py
"""

from datetime import date
from pathlib import Path
import json
import os
import random
import urllib.request

USER = "AyeshaIrshad1337"
OUT = Path(__file__).resolve().parent.parent / "assets"
W, H = 860, 520
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

NAME = "Ayesha Irshad"
ABOUT = [
    ("Role", "AI Engineer @ Ahoy"),
    ("Also", "Solo founder, building on the side"),
    ("Base", "Karachi, Pakistan"),
    ("Focus", "Multi-agent systems, LLM tooling"),
    ("Stack", "Python, TypeScript, LangGraph, Postgres"),
]
BUILDING = [
    ("Codet.ai", "GTM optimization platform"),
    ("DiffSpy", "Pricing intelligence SaaS"),
    ("NEXUS", "Crypto opportunity scanner"),
]
MOTTO = ("I may not be Alan Turing, but I am confident", "enough to be the next codebreaker.")
LAMP_WORD = "CODEBREAKER"
KEYBOARD = ["QWERTZUIO", "ASDFGHJK", "PYXCVBNML"]  # the real Enigma lamp layout

THEMES = {
    "dark": dict(bg="#161b22", panel="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e",
                 faint="#6e7681", key="#3fb950", head="#a371f7", lamp="#d29922", on_lamp="#0d1117"),
    "light": dict(bg="#f6f8fa", panel="#ffffff", border="#d0d7de", text="#1f2328", muted="#59636e",
                  faint="#818b98", key="#1a7f37", head="#8250df", lamp="#bf8700", on_lamp="#ffffff"),
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

# ---------------------------------------------------------------- data


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    return payload["data"]["user"]


def streaks(days):
    """Current and longest run of days with at least one contribution.

    Today does not break the current streak if nothing has been pushed yet.
    """
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"] > 0:
            current += 1
        elif i == 0 and d["date"] == date.today().isoformat():
            continue
        else:
            break
    return current, longest


def summarise(user):
    repos = user["repositories"]
    calendar = user["contributionsCollection"]["contributionCalendar"]
    current, longest = streaks([d for w in calendar["weeks"] for d in w["contributionDays"]])
    return {
        "contributions": calendar["totalContributions"],
        "current": current,
        "longest": longest,
        "repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "followers": user["followers"]["totalCount"],
    }

# ---------------------------------------------------------------- drawing


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, fill, size=12.5, weight=None, anchor=None, extra=""):
    attrs = f'x="{x}" y="{y}" fill="{fill}" font-size="{size}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f"<text {attrs}{extra}>{esc(s)}</text>"


def heading(x, y, label, t, width=420):
    """A section title followed by a thin rule, like '— Building ———'."""
    label_w = len(label) * 12.5 * 0.6
    return (text(x, y, label, t["head"], weight="700")
            + f'<line x1="{x + label_w + 10:.1f}" y1="{y - 4}" x2="{x + width}" y2="{y - 4}" stroke="{t["border"]}"/>')


def rows(x, y, pairs, t, key_w=80, step=21):
    out = []
    for key, value in pairs:
        out.append(text(x, y, key, t["key"]))
        out.append(text(x + key_w, y, value, t["text"]))
        y += step
    return "".join(out), y


def decrypt_frames(target, steps=9, seed=7):
    """Frames that turn random capitals into the target, left to right."""
    rnd = random.Random(seed)
    frames = []
    for step in range(steps):
        solved = round(len(target) * step / (steps - 1))
        frames.append("".join(ch if (i < solved or ch == " ") else rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                              for i, ch in enumerate(target)))
    return frames


def name_block(x, y, t):
    """The name decodes out of random letters once, then stays."""
    frames = decrypt_frames(NAME)
    step = 0.12
    out = []
    for i, frame in enumerate(frames):
        begin = i * step
        if i == len(frames) - 1:
            # Visible by default and hidden only while the cipher plays, so a
            # viewer without animation support still shows the name.
            out.append(f'<text x="{x}" y="{y}" fill="{t["text"]}" font-size="24" font-weight="700">{esc(frame)}'
                       f'<set attributeName="opacity" to="0" begin="0s" end="{begin:.2f}s"/></text>')
        else:
            out.append(f'<text x="{x}" y="{y}" fill="{t["head"]}" font-size="24" font-weight="700" opacity="0">{esc(frame)}'
                       f'<set attributeName="opacity" to="1" begin="{begin:.2f}s" end="{begin + step:.2f}s"/></text>')
    return "".join(out)


def enigma(x0, y0, t):
    """Rotor windows over a lamp board. Lamps light one by one to spell LAMP_WORD."""
    slots = len(LAMP_WORD) + 4  # four dark slots before the word repeats
    dur = slots * 0.55
    key_times = ";".join(f"{i / slots:.4f}" for i in range(slots)) + ";1"
    gap, r = 32, 12.5
    board_w = (len(KEYBOARD[0]) - 1) * gap
    out = []

    # rotors: the right one steps on every key press, like the real machine
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    win_w, win_h, win_gap = 44, 30, 16
    rx0 = x0 + (board_w - (3 * win_w + 2 * win_gap)) / 2
    out.append(f'<clipPath id="rotor"><rect width="{win_w}" height="{win_h}" rx="6"/></clipPath>')
    for i, start in enumerate((0, 4, 19)):  # A, E, T
        out.append(f'<g transform="translate({rx0 + i * (win_w + win_gap):.1f},{y0})">')
        out.append(f'<rect width="{win_w}" height="{win_h}" rx="6" fill="{t["panel"]}" stroke="{t["border"]}"/>')
        out.append('<g clip-path="url(#rotor)">')
        if i == 2:
            strip = "".join(text(win_w / 2, 20 + j * win_h, alphabet[(start + j) % 26], t["text"], size=15, weight="700", anchor="middle")
                            for j in range(len(LAMP_WORD) + 1))
            values = [f"0 {-min(s, len(LAMP_WORD)) * win_h}" for s in range(slots)] + ["0 0"]
            out.append(f'<g><animateTransform attributeName="transform" type="translate" values="{";".join(values)}" '
                       f'keyTimes="{key_times}" dur="{dur:.2f}s" calcMode="discrete" repeatCount="indefinite"/>{strip}</g>')
        else:
            out.append(text(win_w / 2, 20, alphabet[start], t["text"], size=15, weight="700", anchor="middle"))
        out.append("</g></g>")

    # lamp board
    ly = y0 + 74
    for row_i, row in enumerate(KEYBOARD):
        row_x = x0 + (len(KEYBOARD[0]) - len(row)) * gap / 2
        for col_i, ch in enumerate(row):
            cx, cy = row_x + col_i * gap, ly + row_i * 36
            out.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="{t["panel"]}" stroke="{t["border"]}"/>')
            out.append(text(f"{cx:.1f}", cy + 4.5, ch, t["faint"], size=11.5, anchor="middle"))
            lit = [1 if i < len(LAMP_WORD) and LAMP_WORD[i] == ch else 0 for i in range(slots)]
            if any(lit):
                values = ";".join(str(v) for v in lit + [lit[0]])
                out.append(f'<g opacity="0"><animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
                           f'dur="{dur:.2f}s" calcMode="discrete" repeatCount="indefinite"/>'
                           f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="{t["lamp"]}"/>'
                           + text(f"{cx:.1f}", cy + 4.5, ch, t["on_lamp"], size=11.5, weight="700", anchor="middle")
                           + "</g>")
    caption_y = ly + 2 * 36 + 40
    out.append(text(x0 + board_w / 2, caption_y, "the lamps spell what I like doing", t["faint"], size=10.5, anchor="middle"))
    return "".join(out)


def build(stats, t):
    x = 32
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" aria-label="Ayesha Irshad, AI engineer at Ahoy and solo founder">',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        text(x, 46, "ayesha@codebreaker", t["muted"], size=12),
        name_block(x, 78, t),
    ]
    y = 118
    p.append(heading(x, y, "About", t))
    block, y = rows(x, y + 26, ABOUT, t)
    p.append(block)

    y += 14
    p.append(heading(x, y, "Building", t))
    block, y = rows(x, y + 26, BUILDING, t)
    p.append(block)

    y += 14
    p.append(heading(x, y, "GitHub", t))
    github = [
        ("Activity", f'{stats["contributions"]:,} contributions in the last year'),
        ("Streak", f'{stats["current"]} days now, longest {stats["longest"]}'),
        ("Repos", f'{stats["repos"]} public · {stats["stars"]} stars · {stats["followers"]} followers'),
    ]
    block, y = rows(x, y + 26, github, t)
    p.append(block)

    y += 18
    p.append(text(x, y, MOTTO[0], t["muted"], size=12, extra=' font-style="italic"'))
    p.append(text(x, y + 18, MOTTO[1], t["muted"], size=12, extra=' font-style="italic"'))
    cursor_x = x + len(MOTTO[1]) * 12 * 0.6 + 6
    p.append(f'<rect x="{cursor_x:.1f}" y="{y + 7}" width="7" height="14" fill="{t["key"]}">'
             '<animate attributeName="opacity" values="1;0;1" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/></rect>')

    p.append(enigma(560, 175, t))
    p.append("</svg>")
    return "\n".join(p) + "\n"


def main():
    stats = summarise(fetch())
    OUT.mkdir(exist_ok=True)
    for theme, tokens in THEMES.items():
        path = OUT / f"card-{theme}.svg"
        path.write_text(build(stats, tokens), encoding="utf-8")
        print("wrote", path.relative_to(OUT.parent))
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
