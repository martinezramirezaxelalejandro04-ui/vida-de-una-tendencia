"""How long does a topic stay among the most-read Wikipedia articles in Mexico?

Vocabulary used in this module:

  appearance   an article is on the list of a given day
  episode      a run of consecutive days on the list (a "trend")
  evergreen    an article that is on the list most of the year (not a trend)

The list of each day only includes articles above a view threshold that
Wikimedia applies to protect reader privacy, so "leaving the list" means
falling below that threshold, not dropping to zero.
"""
from __future__ import annotations

import pandas as pd

EVERGREEN_SHARE = 0.5      # on the list more than half of the days: not a trend


def articles_only(table: pd.DataFrame) -> pd.DataFrame:
    """Spanish Wikipedia articles, without portals, search pages and other special pages."""
    spanish = table[table["project"] == "es.wikipedia"]
    return spanish[~spanish["article"].str.contains(":", regex=False)].copy()


def add_day_number(table: pd.DataFrame) -> pd.DataFrame:
    """Number the available days 0, 1, 2... so a day without data does not break a run."""
    days = {day: number for number, day in enumerate(sorted(table["date"].unique()))}
    return table.assign(day_number=table["date"].map(days))


def episodes(table: pd.DataFrame) -> pd.DataFrame:
    """One row per trend: when it started, how long it lasted and how high it peaked."""
    table = add_day_number(articles_only(table)).sort_values(["article", "day_number"])
    total_days = table["day_number"].nunique()
    presence = table.groupby("article")["day_number"].transform("nunique") / total_days
    table = table[presence <= EVERGREEN_SHARE]

    new_run = table.groupby("article")["day_number"].diff().ne(1)
    table = table.assign(episode=new_run.groupby(table["article"]).cumsum())
    runs = table.groupby(["article", "episode"])
    result = runs.agg(start=("date", "min"), first_day=("day_number", "min"),
                      last_day=("day_number", "max"), days=("day_number", "count"),
                      peak_views=("views", "max"), first_day_views=("views", "first")
                      ).reset_index()
    peak_position = runs["views"].apply(lambda views: int(views.to_numpy().argmax()))
    result["peak_on_day"] = peak_position.to_numpy() + 1
    # A run touching the first or last day may have started before or continued after.
    complete = (result["first_day"] > 0) & (result["last_day"] < total_days - 1)
    return result[complete].drop(columns=["episode", "first_day", "last_day"]).reset_index(drop=True)


def duration_summary(trends: pd.DataFrame) -> dict:
    return {
        "trends": len(trends),
        "last_one_day_pct": round(100 * (trends["days"] == 1).mean(), 1),
        "last_three_days_or_less_pct": round(100 * (trends["days"] <= 3).mean(), 1),
        "last_a_week_or_more_pct": round(100 * (trends["days"] >= 7).mean(), 1),
        "median_days": float(trends["days"].median()),
        "mean_days": round(trends["days"].mean(), 2),
        "peak_on_first_day_pct": round(100 * (trends["peak_on_day"] == 1).mean(), 1),
    }


def survival(trends: pd.DataFrame, horizon: int = 14) -> pd.DataFrame:
    """Share of trends still on the list on their 1st, 2nd, 3rd... day."""
    return pd.DataFrame({
        "day": range(1, horizon + 1),
        "still_trending_pct": [round(100 * (trends["days"] >= day).mean(), 1)
                               for day in range(1, horizon + 1)],
    })


def by_size(trends: pd.DataFrame) -> pd.DataFrame:
    """Do bigger trends last longer? Trends grouped by the height of their peak."""
    labels = ["Pequeñas (tercio inferior)", "Medianas", "Grandes (tercio superior)"]
    size = pd.qcut(trends["peak_views"].rank(method="first"), 3, labels=labels)
    table = trends.groupby(size, observed=True).agg(
        trends=("days", "count"), typical_peak_views=("peak_views", "median"),
        median_days=("days", "median"), mean_days=("days", "mean"),
        last_one_day_pct=("days", lambda days: 100 * (days == 1).mean()))
    return table.round(1).rename_axis("size").reset_index()
