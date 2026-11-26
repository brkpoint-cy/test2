import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

AIR_ALIASES = {
    "time": "time", "日期": "time", "日期时间": "time", "时间": "time",
    "aqi": "aqi", "AQI": "aqi", "pm25": "pm25", "PM2.5": "pm25",
    "PM2_5": "pm25", "pm10": "pm10", "PM10": "pm10", "so2": "so2",
    "SO2": "so2", "no2": "no2", "NO2": "no2", "co": "co", "CO": "co",
    "o3": "o3", "O3": "o3",
}
WEATHER_ALIASES = {
    "time": "time", "日期": "time", "日期时间": "time", "时间": "time",
    "temperature_2m": "temperature", "temperature": "temperature", "温度": "temperature",
    "relative_humidity_2m": "humidity", "humidity": "humidity", "相对湿度": "humidity",
    "wind_speed_10m": "wind_speed", "wind_speed": "wind_speed", "风速": "wind_speed",
    "wind_direction_10m": "wind_direction", "wind_direction": "wind_direction", "风向": "wind_direction",
    "surface_pressure": "pressure", "pressure": "pressure", "气压": "pressure",
    "precipitation": "precipitation", "降水": "precipitation",
}
POLLUTANTS = ["aqi", "pm25", "pm10", "so2", "no2", "co", "o3"]
WEATHER_COLUMNS = ["temperature", "humidity", "wind_speed", "wind_direction", "pressure", "precipitation"]


def _read_csv(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="gb18030")


def _canonicalize(frame: pd.DataFrame, aliases: dict[str, str], required: list[str]) -> pd.DataFrame:
    selected = {}
    for original, canonical in aliases.items():
        if original in frame.columns and canonical not in selected:
            selected[canonical] = frame[original]
    missing = [column for column in required if column not in selected]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    result = pd.DataFrame(selected)
    try:
        timestamps = pd.to_datetime(result["time"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid timestamp in data: {exc}") from exc
    if timestamps.isna().any():
        row = int(np.flatnonzero(timestamps.isna().to_numpy())[0]) + 2
        raise ValueError(f"Missing timestamp in time at CSV row {row}")
    if timestamps.dt.tz is not None:
        timestamps = timestamps.dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    result["time"] = timestamps.dt.floor("h")
    for column in result.columns.drop("time"):
        converted = pd.to_numeric(result[column], errors="coerce")
        invalid = result[column].notna() & converted.isna()
        if column == "pm25" and invalid.any():
            index = int(np.flatnonzero(invalid.to_numpy())[0])
            raise ValueError(f"Invalid pm25 value {result[column].iloc[index]!r} at CSV row {index + 2}")
        result[column] = converted
    return result[["time", *result.columns.drop("time")]]


def load_air_quality(path: Path) -> pd.DataFrame:
    frame = _canonicalize(_read_csv(path), AIR_ALIASES, ["time", "pm25"])
    numeric = frame.columns.drop("time")
    frame[numeric] = frame[numeric].mask(frame[numeric] < 0)
    return frame


def load_weather(path: Path) -> pd.DataFrame:
    frame = _canonicalize(_read_csv(path), WEATHER_ALIASES, ["time"])
    nonnegative = [column for column in ["humidity", "wind_speed", "wind_direction", "pressure", "precipitation"] if column in frame]
    if nonnegative:
        frame[nonnegative] = frame[nonnegative].mask(frame[nonnegative] < 0)
    return frame


def make_demo_data(output: Path, years: int = 3, seed: int = 42) -> pd.DataFrame:
    if years < 1:
        raise ValueError("years must be at least 1")
    output = Path(output)
    rng = np.random.default_rng(seed)
    times = pd.date_range("2021-01-01", periods=365 * 24 * years, freq="h")
    n = len(times)
    winter = np.isin(times.month, [10, 11, 12, 1, 2, 3, 4]).astype(float)
    daily = np.sin(2 * np.pi * (times.hour.to_numpy() - 7) / 24)
    noise = rng.normal(size=n)
    ar = np.zeros(n)
    for i in range(1, n):
        ar[i] = 0.985 * ar[i - 1] + noise[i]
    episodes = np.zeros(n)
    for start in rng.choice(np.arange(72, n - 72), size=max(12, 18 * years), replace=False):
        length = int(rng.integers(18, 72))
        amplitude = rng.uniform(35, 100)
        episodes[start:start + length] += amplitude * np.sin(np.linspace(0, np.pi, length))
    temperature = 5 - 17 * winter + 10 * np.sin(2 * np.pi * (times.dayofyear.to_numpy() - 172) / 365) + rng.normal(0, 3, n)
    humidity = np.clip(58 + 12 * winter + rng.normal(0, 9, n), 15, 100)
    wind_speed = np.clip(rng.gamma(2.2, 1.1, n) + 0.8 * winter, 0.1, None)
    pm25 = np.maximum(0, 24 + 25 * winter + 9 * daily + 5 * ar + episodes - 2.2 * wind_speed + 0.12 * humidity)
    frame = pd.DataFrame({
        "time": times,
        "aqi": np.maximum(0, pm25 * 1.35 + rng.normal(0, 6, n)),
        "pm25": pm25,
        "pm10": np.maximum(0, pm25 * 1.55 + rng.normal(0, 12, n)),
        "so2": np.maximum(0, 7 + 10 * winter + rng.normal(0, 3, n)),
        "no2": np.maximum(0, 25 + 15 * winter + 0.15 * pm25 + rng.normal(0, 6, n)),
        "co": np.maximum(0, 0.5 + 0.35 * winter + 0.005 * pm25 + rng.normal(0, 0.1, n)),
        "o3": np.maximum(0, 55 - 18 * winter - 0.12 * pm25 + rng.normal(0, 9, n)),
    })
    weather = pd.DataFrame({
        "time": times,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "wind_direction": rng.uniform(0, 360, n),
        "pressure": 985 + rng.normal(0, 6, n),
        "precipitation": np.where(rng.random(n) < 0.05, rng.exponential(0.8, n), 0),
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    weather_path = output.with_name("weather.csv")
    weather.to_csv(weather_path, index=False)
    metadata = {
        "data_source": "synthetic", "seed": seed, "rows": n,
        "start": str(times[0]), "end": str(times[-1]),
        "warning": "Synthetic data for software demonstration only; not observed Changchun air quality.",
    }
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return frame


def download_weather(output: Path, start: str, end: str, latitude: float = 43.88, longitude: float = 125.35) -> pd.DataFrame:
    params = {
        "latitude": latitude, "longitude": longitude, "start_date": start, "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation",
        "timezone": "Asia/Shanghai",
    }
    response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Open-Meteo request failed ({response.status_code}): {response.text[:300]}")
    hourly = response.json().get("hourly", {})
    if not hourly.get("time"):
        raise RuntimeError("Open-Meteo response contains no hourly data")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(hourly).to_csv(output, index=False)
    output.with_suffix(".metadata.json").write_text(json.dumps({
        "data_source": "Open-Meteo Historical Weather API", "request": params,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return load_weather(output)
