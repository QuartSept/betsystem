"""Rapor yardımcıları."""

import pandas as pd


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Veri yok._"
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)
