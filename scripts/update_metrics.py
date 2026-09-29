#!/usr/bin/env python3
"""Generate the profile README language card from public GitHub data."""

from __future__ import annotations

import html
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "most-commit-language.svg"
PALETTE = ["#4F8F8B", "#6BA8A4", "#D9B38C", "#2E5D62", "#8FD3D0"]
IGNORED = {"Profile README", "christiano-gonara"}


def request_json(url: str, token: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "christiano-gonara-profile-metrics",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_languages(username: str, token: str) -> dict[str, int]:
    repos = request_json(
        f"{API}/users/{urllib.parse.quote(username)}/repos?per_page=100&type=owner&sort=updated",
        token,
    )
    if not isinstance(repos, list):
        raise RuntimeError("GitHub returned an unexpected repository response")

    totals: dict[str, int] = {}
    for repo in repos:
        if not isinstance(repo, dict) or repo.get("fork"):
            continue
        name = str(repo.get("name", ""))
        if name in IGNORED:
            continue
        languages_url = repo.get("languages_url")
        if not languages_url:
            continue
        languages = request_json(str(languages_url), token)
        if not isinstance(languages, dict):
            continue
        for language, bytes_count in languages.items():
            if isinstance(bytes_count, int):
                totals[str(language)] = totals.get(str(language), 0) + bytes_count

    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5])


def arc_path(cx: float, cy: float, radius: float, start: float, end: float) -> str:
    start_rad = math.radians(start - 90)
    end_rad = math.radians(end - 90)
    x1, y1 = cx + radius * math.cos(start_rad), cy + radius * math.sin(start_rad)
    x2, y2 = cx + radius * math.cos(end_rad), cy + radius * math.sin(end_rad)
    large_arc = 1 if end - start > 180 else 0
    return f"M {cx} {cy} L {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"


def render_card(languages: dict[str, int]) -> str:
    if not languages:
        languages = {"No language data": 1}
    total = sum(languages.values())
    title = "Top Languages"
    parts = [
        '<svg role="img" aria-labelledby="title desc" width="495" height="200" viewBox="0 0 495 200" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="title">{title}</title>',
        '<desc id="desc">Linguagens mais presentes nos repositórios públicos</desc>',
        '<rect x="1" y="1" width="493" height="198" rx="10" fill="#081B2B" stroke="#2E5D62"/>',
        '<style>text{font-family:Segoe UI,Ubuntu,Helvetica Neue,sans-serif}.title{font-size:22px;font-weight:600;fill:#D9B38C}.label{font-size:14px;font-weight:600;fill:#8FD3D0}</style>',
        f'<text x="28" y="42" class="title">{title}</text>',
    ]

    cx, cy, radius = 365, 108, 65
    current = 0.0
    for index, (language, amount) in enumerate(languages.items()):
        sweep = amount / total * 360
        end = current + sweep
        color = PALETTE[index % len(PALETTE)]
        if sweep >= 359.99:
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}"/>')
        else:
            parts.append(f'<path d="{arc_path(cx, cy, radius, current, end)}" fill="{color}"/>')
        current = end

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="#081B2B"/>')
    legend_y = 76
    for index, (language, amount) in enumerate(languages.items()):
        color = PALETTE[index % len(PALETTE)]
        percentage = amount / total * 100
        safe_language = html.escape(language)
        parts.append(f'<rect x="28" y="{legend_y - 11}" width="16" height="16" rx="2" fill="{color}"/>')
        parts.append(f'<text x="54" y="{legend_y + 2}" class="label">{safe_language} · {percentage:.1f}%</text>')
        legend_y += 23

    parts.append("</svg>")
    return "".join(parts) + "\n"


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GITHUB_REPOSITORY_OWNER", "christiano-gonara")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    try:
        languages = fetch_languages(username, token)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(render_card(languages), encoding="utf-8")
        print("Updated", OUTPUT)
        print(json.dumps(languages, ensure_ascii=False, sort_keys=False))
        return 0
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as error:
        print(f"Could not update metrics: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
