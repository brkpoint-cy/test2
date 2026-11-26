"""Download real Changchun air-quality + weather data from Open-Meteo and convert to project CSV format."""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

LAT, LON = 43.88, 125.35
START, END = "2023-11-18", "2026-11-17"
TZ = "Asia/Shanghai"
OUT = Path("data/raw")


def fetch(url: str, params: dict, retries: int = 4) -> dict:
    for attempt in range(retries):
        response = requests.get(url, params=params, timeout=120)
        if response.status_code == 200:
            return response.json()
        print(f"  retry {attempt + 1}: HTTP {response.status_code} {response.text[:200]}", flush=True)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed: {url}")


def year_ranges(start: str, end: str):
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    current = start_ts
    while current <= end_ts:
        chunk_end = min(current + pd.DateOffset(years=1) - pd.DateOffset(days=1), end_ts)
        yield current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        current = chunk_end + pd.DateOffset(days=1)


def download_air() -> pd.DataFrame:
    frames = []
    for s, e in year_ranges(START, END):
        print(f"air {s} -> {e}", flush=True)
        data = fetch("https://air-quality-api.open-meteo.com/v1/air-quality", {
            "latitude": LAT, "longitude": LON, "start_date": s, "end_date": e,
            "hourly": "pm2_5,pm10,sulphur_dioxide,nitrogen_dioxide,carbon_monoxide,ozone",
            "timezone": TZ,
        })
        frames.append(pd.DataFrame(data["hourly"]))
    frame = pd.concat(frames, ignore_index=True).rename(columns={
        "pm2_5": "pm25", "sulphur_dioxide": "so2", "nitrogen_dioxide": "no2",
        "carbon_monoxide": "co", "ozone": "o3",
    })
    frame["time"] = frame["time"].str.replace("T", " ")
    # Open-Meteo 的 CO 单位为 μg/m³，转为与常规一致的 mg/m³
    frame["co"] = frame["co"] / 1000.0
    return frame[["time", "pm25", "pm10", "so2", "no2", "co", "o3"]]


def download_weather() -> pd.DataFrame:
    frames = []
    for s, e in year_ranges(START, END):
        print(f"weather {s} -> {e}", flush=True)
        data = fetch("https://archive-api.open-meteo.com/v1/archive", {
            "latitude": LAT, "longitude": LON, "start_date": s, "end_date": e,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation",
            "timezone": TZ,
        })
        frames.append(pd.DataFrame(data["hourly"]))
    frame = pd.concat(frames, ignore_index=True).rename(columns={
        "temperature_2m": "temperature", "relative_humidity_2m": "humidity",
        "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_direction",
        "surface_pressure": "pressure",
    })
    frame["time"] = frame["time"].str.replace("T", " ")
    return frame[["time", "temperature", "humidity", "wind_speed", "wind_direction", "pressure", "precipitation"]]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    air = download_air()
    weather = download_weather()
    air_path = OUT / "changchun_air_observed.csv"
    weather_path = OUT / "changchun_weather_observed.csv"
    air.to_csv(air_path, index=False)
    weather.to_csv(weather_path, index=False)
    meta = {
        "data_source": "observed",
        "provider": "Open-Meteo CAMS Air Quality + Historical Weather",
        "latitude": LAT, "longitude": LON,
        "rows": len(air), "start": air["time"].iloc[0], "end": air["time"].iloc[-1],
        "nulls": {c: int(air[c].isna().sum()) for c in air.columns if air[c].isna().any()},
    }
    air_path.with_suffix(".metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False), flush=True)
    print(f"weather rows={len(weather)} {weather['time'].iloc[0]} -> {weather['time'].iloc[-1]}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
