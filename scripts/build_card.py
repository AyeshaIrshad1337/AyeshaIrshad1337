"""Build the profile card, in a dark and a light version.

One card holds the whole profile: who I am, what I am building, live GitHub
numbers and the motto on the left, and an animated rubber duck on the right
(see duck.py). It is plain SVG with SMIL animation, so it plays
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

from duck import duck_svg

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

THEMES = {
    "dark": dict(bg="#161b22", panel="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e",
                 faint="#6e7681", key="#3fb950", head="#e3b341"),
    "light": dict(bg="#f6f8fa", panel="#ffffff", border="#d0d7de", text="#1f2328", muted="#59636e",
                  faint="#818b98", key="#1a7f37", head="#9a6700"),
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


def build(stats, theme):
    t = THEMES[theme]
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

    p.append(duck_svg(540, 150, theme, t["muted"], t["faint"]))
    p.append("</svg>")
    return "\n".join(p) + "\n"


def main():
    stats = summarise(fetch())
    OUT.mkdir(exist_ok=True)
    for theme, tokens in THEMES.items():
        path = OUT / f"card-{theme}.svg"
        path.write_text(build(stats, theme), encoding="utf-8")
        print("wrote", path.relative_to(OUT.parent))
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
