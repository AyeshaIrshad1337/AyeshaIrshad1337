"""Build the GitHub stats card from the GitHub API, in a dark and a light version.

This replaces the third-party stats and streak cards, which kept breaking.
It needs a token in GITHUB_TOKEN (the workflow's own token is enough) and
uses only the standard library.

Run from the repository root:  GITHUB_TOKEN=... python3 scripts/build_stats.py
"""

from datetime import date
from pathlib import Path
import json
import os
import urllib.request

USER = os.environ.get("PROFILE_USER", "AyeshaIrshad1337")
OUT = Path(__file__).resolve().parent.parent / "assets"
W, H = 850, 190
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
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

THEMES = {
    "dark": dict(bg="#0a0e17", bar="#0f1525", border="#1a2340", panel="#111827",
                 text="#c9d1d9", muted="#6b7a99", faint="#3d4f6f",
                 green="#00ff9f", purple="#7b61ff", pink="#ff6ac1", gold="#ffbd2e"),
    "light": dict(bg="#f6f8fa", bar="#eaeef2", border="#d0d7de", panel="#ffffff",
                  text="#1f2328", muted="#57606a", faint="#8c959f",
                  green="#0a7d55", purple="#5b3fd6", pink="#b8327f", gold="#b7791f"),
}


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
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
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)

    sizes, colors = {}, {}
    for repo in repos["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#8b949e"
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:6]
    languages = [(name, size / total, colors[name]) for name, size in top]

    return {
        "contributions": calendar["totalContributions"],
        "current": current,
        "longest": longest,
        "repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "followers": user["followers"]["totalCount"],
        "languages": languages,
    }


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, fill, size=12, weight=None, anchor=None):
    attrs = f'x="{x}" y="{y}" fill="{fill}" font-size="{size}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f"<text {attrs}>{esc(s)}</text>"


def build(stats, theme):
    t = THEMES[theme]
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" aria-label="GitHub stats for {USER}">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}"/>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}"/>',
        f'<path d="M0.5 32V10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10V32z" fill="{t["bar"]}"/>',
        f'<line x1="0" y1="32.5" x2="{W}" y2="32.5" stroke="{t["border"]}"/>',
        '<circle cx="18" cy="16" r="5.5" fill="#ff5f56"/>',
        '<circle cx="36" cy="16" r="5.5" fill="#ffbd2e"/>',
        '<circle cx="54" cy="16" r="5.5" fill="#27c93f"/>',
        text(W / 2, 20, "gh stats --last-year", t["faint"], size=11.5, anchor="middle"),
    ]

    tiles = [
        (f'{stats["contributions"]:,}', "contributions", t["green"]),
        (f'{stats["current"]}d', "current streak", t["gold"]),
        (f'{stats["longest"]}d', "longest streak", t["pink"]),
        (str(stats["repos"]), "repositories", t["purple"]),
        (str(stats["stars"]), "stars earned", t["gold"]),
        (str(stats["followers"]), "followers", t["green"]),
    ]
    tw, th, gap = 128, 60, 10
    for i, (value, label, color) in enumerate(tiles):
        x = 20 + (i % 3) * (tw + gap)
        y = 46 + (i // 3) * (th + gap)
        p.append(f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="8" fill="{t["panel"]}" stroke="{t["border"]}"/>')
        p.append(text(x + 14, y + 30, value, color, size=20, weight="700"))
        p.append(text(x + 14, y + 48, label, t["muted"], size=10.5))

    # languages
    lx, lw = 450, 380
    p.append(text(lx, 62, "most used languages, by code size", t["faint"], size=11))
    p.append(f'<clipPath id="bar"><rect x="{lx}" y="74" width="{lw}" height="10" rx="5"/></clipPath>')
    p.append(f'<g clip-path="url(#bar)"><rect x="{lx}" y="74" width="{lw}" height="10" fill="{t["border"]}"/>')
    shown = sum(share for _, share, _ in stats["languages"]) or 1
    x = lx
    for name, share, color in stats["languages"]:
        width = lw * share / shown
        p.append(f'<rect x="{x:.1f}" y="74" width="{width:.1f}" height="10" fill="{color}"/>')
        x += width
    p.append("</g>")
    for i, (name, share, color) in enumerate(stats["languages"]):
        cx = lx + (i % 2) * 190
        cy = 112 + (i // 2) * 24
        p.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>')
        p.append(text(cx + 18, cy, name, t["text"], size=12))
        p.append(text(cx + 175, cy, f"{share * 100:.1f}%", t["muted"], size=11.5, anchor="end"))

    p.append("</svg>")
    return "\n".join(p) + "\n"


def main():
    stats = summarise(fetch())
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        path = OUT / f"stats-{theme}.svg"
        path.write_text(build(stats, theme), encoding="utf-8")
        print("wrote", path.relative_to(OUT.parent))
    print(json.dumps({k: v for k, v in stats.items() if k != "languages"}))


if __name__ == "__main__":
    main()
