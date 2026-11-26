from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from .features import tabular_features


@dataclass
class Split:
    X: np.ndarray
    tabular: np.ndarray
    y: np.ndarray
    timestamps: np.ndarray
    current_pm25: np.ndarray


@dataclass
class DatasetBundle:
    train: Split
    val: Split
    test: Split
    feature_columns: list[str]
    sequence_scaler: StandardScaler
    tabular_scaler: StandardScaler
    threshold: float
    lookback: int
    horizon: int
    purged: dict[str, int]


def _split(arrays: dict[str, np.ndarray], indices: np.ndarray) -> Split:
    X = arrays["X"][indices]
    return Split(
        X=X,
        tabular=tabular_features(X),
        y=arrays["y"][indices],
        timestamps=arrays["timestamps"][indices],
        current_pm25=arrays["current_pm25"][indices],
    )


def make_windows(
    frame: pd.DataFrame,
    feature_columns: list[str],
    lookback: int,
    horizon: int,
    threshold: float,
    splits: list[float],
) -> DatasetBundle:
    if lookback < 1 or horizon < 1:
        raise ValueError("lookback and horizon must be positive")
    if len(splits) != 3 or any(part <= 0 for part in splits) or abs(sum(splits) - 1) > 1e-8:
        raise ValueError("splits must be three positive fractions summing to 1")
    ordered = frame.sort_values("time").reset_index(drop=True)
    expected = pd.date_range(ordered["time"].iloc[0], periods=len(ordered), freq="h")
    if not ordered["time"].equals(pd.Series(expected, name="time")):
        raise ValueError("Window construction requires a complete hourly time index")
    features = ordered[feature_columns].to_numpy(dtype=np.float32)
    pm25 = ordered["pm25"].to_numpy(dtype=np.float32)
    valid = np.isfinite(features).all(axis=1) & np.isfinite(pm25)
    span = lookback + horizon
    complete = np.convolve(valid.astype(int), np.ones(span, dtype=int), mode="valid") == span
    origins = np.flatnonzero(complete) + lookback - 1
    if len(origins) < 10:
        raise ValueError("Not enough complete continuous windows; inspect missing-data log")
    X = np.stack([features[i - lookback + 1:i + 1] for i in origins]).astype(np.float32)
    y = np.array([np.max(pm25[i + 1:i + horizon + 1]) >= threshold for i in origins], dtype=np.int64)
    timestamps = ordered["time"].to_numpy()[origins]
    current_pm25 = pm25[origins]
    n = len(origins)
    train_end = int(n * splits[0])
    val_end = int(n * (splits[0] + splits[1]))
    if train_end < 1 or val_end <= train_end or val_end >= n:
        raise ValueError("Split fractions produce an empty partition")
    purge = lookback + horizon - 1
    train_idx = np.arange(0, train_end)
    val_idx = np.arange(train_end + purge, val_end)
    test_idx = np.arange(val_end + purge, n)
    if min(len(train_idx), len(val_idx), len(test_idx)) < 1:
        raise ValueError("Boundary purging left an empty partition; provide a longer time range")
    arrays = {"X": X, "y": y, "timestamps": timestamps, "current_pm25": current_pm25}
    train = _split(arrays, train_idx)
    val = _split(arrays, val_idx)
    test = _split(arrays, test_idx)
    for name, split in [("train", train), ("val", val), ("test", test)]:
        if len(np.unique(split.y)) < 2:
            raise ValueError(f"{name} partition has only one event class; adjust the research period or predeclared threshold")
    sequence_scaler = StandardScaler()
    sequence_scaler.fit(train.X.reshape(-1, len(feature_columns)))
    tabular_scaler = StandardScaler()
    tabular_scaler.fit(train.tabular)
    for split in [train, val, test]:
        shape = split.X.shape
        split.X = sequence_scaler.transform(split.X.reshape(-1, shape[-1])).reshape(shape).astype(np.float32)
        split.tabular = tabular_scaler.transform(split.tabular).astype(np.float32)
    return DatasetBundle(
        train=train, val=val, test=test, feature_columns=feature_columns,
        sequence_scaler=sequence_scaler, tabular_scaler=tabular_scaler,
        threshold=threshold, lookback=lookback, horizon=horizon,
        purged={"validation_start": int(purge), "test_start": int(purge)},
    )
