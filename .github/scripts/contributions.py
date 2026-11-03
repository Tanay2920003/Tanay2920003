"""Render the last year of GitHub contributions as an animated SVG card.

Usage: GITHUB_TOKEN=... python contributions.py <login> <output.svg>
"""
import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": "#151B23",
    "FIRST_QUARTILE": "#0E3D38",
    "SECOND_QUARTILE": "#156B61",
    "THIRD_QUARTILE": "#2AA596",
    "FOURTH_QUARTILE": "#5EEAD4",
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

W, H = 1200, 380
PITCH, CELL = 20, 15
GRID_Y = 178


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    # Today may not have contributions yet; don't break the current streak for it.
    current = 0
    tail = days[:-1] if days and not days[-1]["contributionCount"] else days
    for d in reversed(tail):
        if not d["contributionCount"]:
            break
        current += 1
    return longest, current


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def render(cal):
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    longest, current = streaks(days)
    best = max((d["contributionCount"] for d in days), default=0)

    grid_w = len(weeks) * PITCH - (PITCH - CELL)
    x0 = (W - grid_w) // 2

    cells, labels, last_month = [], [], None
    for wi, week in enumerate(weeks):
        x = x0 + wi * PITCH
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and first.day <= 7 and wi < len(weeks) - 2:
            labels.append(f'<text x="{x}" y="{GRID_Y - 12}" class="mono lbl">{MONTHS[first.month - 1]}</text>')
            last_month = first.month
        for d in week["contributionDays"]:
            row = date.fromisoformat(d["date"]).isoweekday() % 7
            delay = wi * 0.028 + row * 0.03
            n = d["contributionCount"]
            cells.append(
                f'<rect class="c" style="animation-delay:{delay:.2f}s" x="{x}" y="{GRID_Y + row * PITCH}" '
                f'width="{CELL}" height="{CELL}" rx="3.5" fill="{LEVELS[d["contributionLevel"]]}">'
                f'<title>{d["date"]}: {plural(n, "contribution")}</title></rect>'
            )

    stats = [("LONGEST STREAK", plural(longest, "day")), ("CURRENT STREAK", plural(current, "day")), ("BEST DAY", f"{best:,}")]
    stat_svg = []
    for i, (k, v) in enumerate(stats):
        x = W - 56 - (len(stats) - 1 - i) * 170
        stat_svg.append(
            f'<g class="rise" style="animation-delay:{0.25 + i * 0.1:.2f}s">'
            f'<text x="{x}" y="78" class="mono lbl" text-anchor="end">{k}</text>'
            f'<text x="{x}" y="112" class="sans" font-size="26" font-weight="600" fill="#E6EDF3" text-anchor="end">{v}</text></g>'
        )

    legend_x = W - 56 - 52 - 5 * PITCH + (PITCH - CELL)
    legend = "".join(
        f'<rect x="{legend_x + i * PITCH}" y="{H - 52}" width="{CELL}" height="{CELL}" rx="3.5" fill="{c}"/>'
        for i, c in enumerate(LEVELS.values())
    )
    grid_h = 7 * PITCH
    sweep_end = grid_w + 160

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
  <title id="title">GitHub contributions</title>
  <desc id="desc">{plural(cal["totalContributions"], "contribution")} in the last year. Longest streak {plural(longest, "day")}, current streak {plural(current, "day")}.</desc>
  <style>
    .mono{{font-family:ui-monospace,SFMono-Regular,Menlo,'DejaVu Sans Mono','Liberation Mono',monospace}}
    .sans{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif}}
    .lbl{{font-size:13px;letter-spacing:2px;fill:#7D8590}}
    .c{{transform-box:fill-box;transform-origin:center;opacity:0;animation:pop .55s cubic-bezier(.2,.8,.2,1) forwards}}
    @keyframes pop{{from{{opacity:0;transform:scale(.2)}}to{{opacity:1;transform:none}}}}
    .rise{{opacity:0;animation:rise .8s cubic-bezier(.2,.8,.2,1) forwards}}
    @keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
    .sweep{{opacity:0;animation:sweep 7s cubic-bezier(.5,0,.5,1) 2.2s infinite}}
    @keyframes sweep{{0%{{opacity:1;transform:translateX(0)}}60%{{opacity:1;transform:translateX({sweep_end}px)}}61%,100%{{opacity:0;transform:translateX({sweep_end}px)}}}}
    .live{{transform-box:fill-box;transform-origin:center;animation:live 2s ease-out infinite}}
    @keyframes live{{from{{transform:scale(1);opacity:.7}}to{{transform:scale(3.2);opacity:0}}}}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.c,.rise{{opacity:1}}}}
  </style>
  <defs>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="20"/></clipPath>
    <clipPath id="grid"><rect x="{x0}" y="{GRID_Y}" width="{grid_w}" height="{grid_h}"/></clipPath>
    <linearGradient id="band" x1="0" x2="1">
      <stop offset="0" stop-color="#5EEAD4" stop-opacity="0"/>
      <stop offset=".5" stop-color="#5EEAD4" stop-opacity=".22"/>
      <stop offset="1" stop-color="#5EEAD4" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="#0A0C10"/></g>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="#1F2630"/>

  <g class="rise" style="animation-delay:.05s">
    <circle cx="61" cy="73" r="4" fill="#5EEAD4" class="live"/>
    <circle cx="61" cy="73" r="4" fill="#5EEAD4"/>
    <text x="76" y="78" class="mono lbl">CONTRIBUTIONS · LAST 12 MONTHS</text>
    <text x="54" y="128" class="sans" font-size="46" font-weight="700" letter-spacing="-1.5" fill="#E6EDF3">{cal["totalContributions"]:,}</text>
  </g>
  {"".join(stat_svg)}

  {"".join(labels)}
  {"".join(cells)}
  <g clip-path="url(#grid)"><rect class="sweep" x="{x0 - 160}" y="{GRID_Y}" width="160" height="{grid_h}" fill="url(#band)"/></g>

  <text x="56" y="{H - 40}" class="mono lbl">UPDATED {date.today().isoformat()}</text>
  <text x="{legend_x - 12}" y="{H - 40}" class="mono lbl" text-anchor="end">LESS</text>
  {legend}
  <text x="{W - 56}" y="{H - 40}" class="mono lbl" text-anchor="end">MORE</text>
</svg>
'''


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
    with open(out, "w") as f:
        f.write(render(fetch(login, token)))
