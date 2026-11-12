"""Run the whole analysis:  python -m tendencias   (after: python -m tendencias.data)"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .analysis import by_size, duration_summary, episodes, survival
from .data import load

OUTPUT = Path(__file__).resolve().parent.parent / "output"
SURFACE, INK, INK_SECONDARY, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
AXIS, BLUE, LIGHT_BLUE = "#c3c2b7", "#2a78d6", "#9ec5f4"
SOURCE = ("Fuente: Wikimedia Pageviews API, artículos más leídos en México, "
          "octubre 2025 a septiembre 2026.")


def _figure(title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    fig.text(0.02, 0.95, title, fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.87, subtitle, fontsize=9.5, color=INK_SECONDARY, va="top")
    fig.text(0.02, 0.03, SOURCE, fontsize=8, color=MUTED, va="bottom")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.yaxis.set_visible(False)
    return fig, ax


def survival_chart(table: pd.DataFrame, path: Path) -> None:
    second_day = table.loc[table["day"] == 2, "still_trending_pct"].iloc[0]
    fig, ax = _figure(
        f"Al segundo día solo sigue {second_day:.0f}% de las tendencias",
        "De cada 100 temas que entran a lo más leído en México, cuántos siguen ahí cada día.")
    colors = [BLUE if day <= 3 else LIGHT_BLUE for day in table["day"]]
    bars = ax.bar(table["day"], table["still_trending_pct"], width=0.7, color=colors)
    for bar, value in zip(bars, table["still_trending_pct"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f"{value:.0f}", ha="center",
                fontsize=9, color=INK)
    ax.set_xticks(table["day"], [f"Día {day}" if day == 1 else str(day) for day in table["day"]])
    ax.set_ylim(0, 112)
    fig.subplots_adjust(left=0.03, right=0.98, top=0.76, bottom=0.16)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def size_chart(table: pd.DataFrame, path: Path) -> None:
    fig, ax = _figure("Las tendencias grandes duran más, pero también se apagan rápido",
                      "Duración promedio en días según el tamaño del pico de lecturas.")
    labels = [f"{row.size}\n(pico típico: {row.typical_peak_views:,.0f} lecturas)"
              for row in table.itertuples()]
    bars = ax.bar(labels, table["mean_days"], width=0.55, color=BLUE)
    for bar, value in zip(bars, table["mean_days"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.08, f"{value:.1f} días",
                ha="center", fontsize=11, color=INK)
    ax.set_ylim(0, table["mean_days"].max() * 1.2)
    fig.subplots_adjust(left=0.03, right=0.98, top=0.76, bottom=0.2)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    (OUTPUT / "charts").mkdir(parents=True, exist_ok=True)
    trends = episodes(load())
    summary, curve, sizes = duration_summary(trends), survival(trends), by_size(trends)
    pd.DataFrame([summary]).to_csv(OUTPUT / "duration_summary.csv", index=False)
    curve.to_csv(OUTPUT / "survival_by_day.csv", index=False)
    sizes.to_csv(OUTPUT / "duration_by_size.csv", index=False, encoding="utf-8-sig")
    (trends["days"].value_counts().sort_index().rename("trends").rename_axis("days")
     .reset_index().to_csv(OUTPUT / "trends_by_duration.csv", index=False))
    survival_chart(curve, OUTPUT / "charts" / "survival.png")
    size_chart(sizes, OUTPUT / "charts" / "duration_by_size.png")
    print(summary)
    print(curve.T.to_string())
    print(sizes.to_string(index=False).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
