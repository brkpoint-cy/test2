import numpy as np
import pandas as pd


def _missing_runs(missing: pd.Series) -> list[int]:
    groups = missing.ne(missing.shift()).cumsum()
    return [int(len(group)) for group in missing[missing].groupby(groups[missing])]


def prepare_hourly(air: pd.DataFrame, weather: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    if air.empty:
        raise ValueError("Air-quality data is empty")
    duplicate_rows = int(air.duplicated("time").sum())
    air = air.groupby("time", as_index=False).mean(numeric_only=True).sort_values("time")
    if weather is not None:
        duplicate_rows += int(weather.duplicated("time").sum())
        weather = weather.groupby("time", as_index=False).mean(numeric_only=True).sort_values("time")
        frame = air.merge(weather, on="time", how="outer", validate="one_to_one")
    else:
        frame = air.copy()
    frame = frame.sort_values("time").set_index("time")
    full_index = pd.date_range(frame.index.min(), frame.index.max(), freq="h")
    frame = frame.reindex(full_index)
    frame.index.name = "time"
    missing_rates = frame.isna().mean().round(6).to_dict()
    log = {
        "rows_after_alignment": len(frame),
        "duplicate_rows_aggregated": duplicate_rows,
        "start": str(frame.index.min()),
        "end": str(frame.index.max()),
        "missing_rates": missing_rates,
        "pm25_missing_run_lengths": _missing_runs(frame["pm25"].isna()),
        "interpolation": "none",
        "timezone": "Asia/Shanghai (naive local hourly timestamps)",
    }
    return frame.reset_index(), log
