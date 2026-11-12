"""Download the daily list of most-read Wikipedia articles in Mexico.

Source: Wikimedia Pageviews API, "top per country" endpoint (public domain, CC0).
Each day lists up to 1,000 articles with their rank and an approximate view
count (rounded up to the next hundred to protect reader privacy).

    python -m tendencias.data

Days already downloaded are skipped, so the command can be re-run safely.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top-per-country/MX/all-access/{day}"
USER_AGENT = "vida-de-una-tendencia/0.1 (educational open-data project)"
FIRST_DAY, LAST_DAY = date(2025, 10, 1), date(2026, 9, 30)
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
SECONDS_BETWEEN_REQUESTS = 1.2


def fetch_day(day: date, attempts: int = 5) -> list[dict] | None:
    """Articles of one day, or None when Wikimedia has no data for it."""
    request = urllib.request.Request(API.format(day=day.strftime("%Y/%m/%d")),
                                     headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)["items"][0]["articles"]
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code != 429 or attempt == attempts - 1:
                raise
            time.sleep(15 * (attempt + 1))  # the server asked us to slow down
    return None


def download(first: date = FIRST_DAY, last: date = LAST_DAY, folder: Path = RAW) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    day, missing = first, []
    while day <= last:
        target = folder / f"{day.isoformat()}.json"
        if not target.exists():
            articles = fetch_day(day)
            if articles is None:
                missing.append(day.isoformat())
            else:
                target.write_text(json.dumps(articles), encoding="utf-8")
            time.sleep(SECONDS_BETWEEN_REQUESTS)
        day += timedelta(days=1)
    print(f"Done. {len(list(folder.glob('*.json')))} days on disk, {len(missing)} without data.")


def load(folder: Path = RAW) -> pd.DataFrame:
    """All downloaded days as one table: date, project, article, rank, views."""
    frames = []
    for path in sorted(folder.glob("*.json")):
        frame = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
        frame["date"] = pd.Timestamp(path.stem)
        frames.append(frame)
    table = pd.concat(frames, ignore_index=True)
    return table.rename(columns={"views_ceil": "views"})[
        ["date", "project", "article", "rank", "views"]
    ]


if __name__ == "__main__":
    download()
