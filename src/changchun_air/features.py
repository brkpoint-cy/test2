import numpy as np
import pandas as pd


def add_features(frame: pd.DataFrame, heating_months: list[int] | None = None) -> tuple[pd.DataFrame, list[str]]:
    heating_months = heating_months or [10, 11, 12, 1, 2, 3, 4]
    result = frame.copy()
    pm25 = result["pm25"]
    for lag in [1, 3, 6, 12, 24]:
        result[f"pm25_lag_{lag}"] = pm25.shift(lag)
    for window in [6, 24]:
        result[f"pm25_rolling_mean_{window}"] = pm25.rolling(window, min_periods=window).mean()
        result[f"pm25_rolling_max_{window}"] = pm25.rolling(window, min_periods=window).max()
    for lag in [1, 6, 24]:
        result[f"pm25_change_{lag}"] = pm25.diff(lag)
    hour = result["time"].dt.hour
    weekday = result["time"].dt.dayofweek
    month = result["time"].dt.month
    result["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    result["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    result["weekday_sin"] = np.sin(2 * np.pi * weekday / 7)
    result["weekday_cos"] = np.cos(2 * np.pi * weekday / 7)
    result["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12)
    result["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12)
    result["is_heating_season"] = month.isin(heating_months).astype(float)
    if "wind_direction" in result:
        radians = np.deg2rad(result["wind_direction"])
        result["wind_direction_sin"] = np.sin(radians)
        result["wind_direction_cos"] = np.cos(radians)
    excluded = {"time", "wind_direction", "aqi"}
    feature_columns = [
        column for column in result.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(result[column])
    ]
    return result, feature_columns


def tabular_features(split_x: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(split_x[:, -1, :])
