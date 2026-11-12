import pandas as pd

from tendencias.analysis import articles_only, by_size, duration_summary, episodes, survival

DAYS = pd.date_range("2026-01-01", periods=20, freq="D")


def table(appearances, project="es.wikipedia"):
    """appearances: {article: {day index: views}}. A filler article marks every day as available."""
    rows = [{"date": DAYS[day], "project": project, "article": article, "rank": 1, "views": views}
            for article, days in appearances.items() for day, views in days.items()]
    rows += [{"date": day, "project": "es.wikipedia", "article": "Siempre", "rank": 2,
              "views": 1000} for day in DAYS]
    return pd.DataFrame(rows)


def trends(appearances):
    return episodes(table(appearances)).set_index("article")


def test_special_pages_and_other_wikis_are_excluded():
    data = table({"Wikipedia:Portada": {3: 9000}, "Especial:Buscar": {3: 9000}, "Dengue": {3: 5000}})
    english = table({"Main_Page": {3: 9000}}, project="en.wikipedia")
    kept = set(articles_only(pd.concat([data, english]))["article"])
    assert "Dengue" in kept and "Siempre" in kept
    assert not {"Wikipedia:Portada", "Especial:Buscar", "Main_Page"} & kept


def test_consecutive_days_form_one_trend_with_its_peak():
    result = trends({"Eclipse": {5: 2000, 6: 9000, 7: 3000}})
    assert result.loc["Eclipse", "days"] == 3
    assert result.loc["Eclipse", "peak_views"] == 9000
    assert result.loc["Eclipse", "peak_on_day"] == 2


def test_a_gap_starts_a_new_trend():
    result = episodes(table({"Final": {3: 5000, 4: 4000, 10: 6000}}))
    assert sorted(result["days"]) == [1, 2]


def test_articles_present_most_days_are_not_trends():
    assert "Siempre" not in trends({"Eclipse": {5: 2000}}).index


def test_trends_touching_the_first_or_last_day_are_left_out():
    result = trends({"Empezó antes": {0: 5000, 1: 4000}, "Sigue después": {18: 4000, 19: 5000},
                     "Completa": {8: 3000}})
    assert list(result.index) == ["Completa"]


def test_a_day_without_data_does_not_break_a_trend():
    data = table({"Eclipse": {5: 2000, 7: 3000}})
    data = data[data["date"] != DAYS[6]]          # Wikimedia has no file for that day
    assert episodes(data).set_index("article").loc["Eclipse", "days"] == 2


def test_summary_and_survival():
    result = episodes(table({"A": {2: 2000}, "B": {4: 2000}, "C": {6: 2000, 7: 2000},
                             "D": {9: 2000, 10: 3000, 11: 2000, 12: 2000}}))
    summary = duration_summary(result)
    assert summary["trends"] == 4
    assert summary["last_one_day_pct"] == 50.0
    assert summary["median_days"] == 1.5
    curve = survival(result, horizon=4).set_index("day")["still_trending_pct"]
    assert list(curve) == [100.0, 50.0, 25.0, 25.0]


def test_size_groups_split_trends_in_thirds_by_peak():
    result = episodes(table({name: {2 + index: 1000 * (index + 1)}
                             for index, name in enumerate("ABCDEF")}))
    groups = by_size(result)
    assert list(groups["trends"]) == [2, 2, 2]
    assert groups["typical_peak_views"].is_monotonic_increasing
