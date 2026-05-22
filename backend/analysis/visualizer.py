from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")


def plot_trending_bar(
    items: list[dict],
    output_path: str | Path,
    title: str = "Trending Topics",
    top_n: int = 20,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(items[:top_n])
    if df.empty:
        return output_path

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["keyword"][::-1], df["count"][::-1], color="steelblue")
    ax.set_xlabel("Count")
    ax.set_title(title)
    plt.tight_layout()
    fig.savefig(output_path, dpi=100)
    plt.close(fig)
    return output_path
