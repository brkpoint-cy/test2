import numpy as np
import pandas as pd


def exploratory_analysis(frame: pd.DataFrame, horizon: int, threshold: float, max_lag: int = 48) -> dict:
    indexed = frame.set_index("time")
    monthly = indexed.groupby(indexed.index.month)["pm25"].agg(["count", "mean", "median", "max"]).reset_index(names="month")
    heating = indexed.assign(
        heating_season=np.where(indexed.index.month.isin([10, 11, 12, 1, 2, 3, 4]), "heating", "non_heating")
    ).groupby("heating_season")["pm25"].agg(["count", "mean", "median", "max"]).reset_index()
    pollutant_columns = [c for c in ["pm25", "pm10", "so2", "no2", "co", "o3"] if c in indexed]
    correlation = indexed[pollutant_columns].corr()
    lag_correlations = []
    for column in [c for c in ["temperature", "humidity", "wind_speed", "pressure", "precipitation"] if c in indexed]:
        for lag in range(max_lag + 1):
            lag_correlations.append({
                "variable": column, "lag_hours": lag,
                "correlation": indexed[column].shift(lag).corr(indexed["pm25"]),
            })
    future_max = indexed["pm25"].rolling(horizon, min_periods=horizon).max().shift(-horizon)
    valid_future = future_max.notna()
    future_event = valid_future & future_max.ge(threshold)
    raw_event = indexed["pm25"].ge(threshold)
    groups = raw_event.ne(raw_event.shift()).cumsum()
    durations = raw_event[raw_event].groupby(groups[raw_event]).size()
    event_count = int(future_event.sum())
    valid_count = int(valid_future.sum())
    return {
        "monthly": monthly,
        "heating_season": heating,
        "pollutant_correlation": correlation,
        "lag_correlations": pd.DataFrame(lag_correlations),
        "event_stats": pd.DataFrame({
            "metric": ["event_windows", "non_event_windows", "unknown_windows", "event_fraction", "event_episodes", "mean_duration_hours", "max_duration_hours"],
            "value": [
                event_count, int((valid_future & ~future_event).sum()), int((~valid_future).sum()),
                float(event_count / valid_count) if valid_count else np.nan, int(len(durations)),
                float(durations.mean()) if len(durations) else np.nan,
                int(durations.max()) if len(durations) else 0,
            ],
        }),
    }
