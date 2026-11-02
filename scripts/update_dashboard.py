"""Generate a self-contained SVG from public GitHub data; no dependencies."""
import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

OWNER = os.environ.get("PROFILE_OWNER", "AnantaUpadhyay")
ROOT = Path(__file__).resolve().parents[1]


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-dashboard"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect():
    user = api(f"/users/{OWNER}")
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    original = [r for r in repos if not r["fork"] and r["name"].lower() != OWNER.lower()]
    languages = Counter()
    for repo in original:
        languages.update(api(f"/repos/{OWNER}/{repo['name']}/languages"))
    return {
        "repos": len(repos), "stars": sum(r["stargazers_count"] for r in original),
        "followers": user["followers"], "forks": sum(r["forks_count"] for r in original),
        "languages": dict(languages), "updated": datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC"),
    }


def render(data):
    colors = ["#b78091", "#9a8baa", "#c5a180", "#91a58e", "#c4ad81"]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="380" viewBox="0 0 960 380" role="img" aria-labelledby="title desc">',
             '<title id="title">Ananta’s public GitHub dashboard</title><desc id="desc">Public repositories, stars, followers, forks and language bytes.</desc>',
             '<rect width="960" height="380" rx="20" fill="#fbf7f4"/>',
             '<rect x="1" y="1" width="958" height="378" rx="19" fill="none" stroke="#e7dcd8"/>',
             '<g font-family="Georgia, serif"><text x="32" y="40" font-size="15" fill="#7e7078">a little of what I do</text>',
             '<circle cx="914" cy="35" r="5" fill="#91a58e"><animate attributeName="opacity" values="1;.35;1" dur="3s" repeatCount="indefinite"/></circle>']
    for i, (key, label) in enumerate([("repos", "repositories"), ("stars", "stars"), ("followers", "followers"), ("forks", "forks")]):
        x = 32 + i * 232
        parts += [f'<rect x="{x}" y="65" width="216" height="105" rx="12" fill="#f3ebe8"/>',
                  f'<text x="{x+18}" y="112" font-size="34" font-weight="700" fill="{colors[i]}">{escape(str(data[key]))}</text>',
                  f'<text x="{x+18}" y="145" font-size="12" fill="#7e7078">{label}</text>']
    parts.append('<text x="32" y="209" font-size="14" fill="#67535f">lately, in code</text>')
    languages = sorted(data["languages"].items(), key=lambda v: v[1], reverse=True)
    if languages:
        selected = languages[:4]
        if len(languages) > 4:
            selected.append(("Other", sum(v for _, v in languages[4:])))
        total = sum(v for _, v in selected)
        x = 32
        for i, (language, value) in enumerate(selected):
            width = 896 * value / total
            parts.append(f'<rect x="{x:.2f}" y="232" width="{width:.2f}" height="16" fill="{colors[i]}"/>')
            x += width
            lx = 32 + i * 180
            parts.append(f'<circle cx="{lx+4}" cy="281" r="4" fill="{colors[i]}"/><text x="{lx+15}" y="286" font-size="12" fill="#67535f">{escape(language)} {value/total:.0%}</text>')
    else:
        parts.append('<text x="32" y="260" font-size="14" fill="#7e7078">Language data will appear after the first refresh.</text>')
    parts.append(f'<path d="M32 316 H928" stroke="#e7dcd8"/><text x="32" y="347" font-size="12" fill="#7e7078">refreshed {escape(data["updated"])} · public GitHub data</text></g></svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    data = collect()
    (ROOT / "assets" / "dashboard.svg").write_text(render(data), encoding="utf-8")
