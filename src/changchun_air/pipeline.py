import json
import shutil
import uuid
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

from .config import load_config
from .data import load_air_quality, load_weather
from .dataset import make_windows
from .eda import exploratory_analysis
from .features import add_features
from .plots import generate_plots
from .preprocessing import prepare_hourly
from .reporting import generate_report
from .training import train_all


def _json_value(value):
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(_json_value(value), ensure_ascii=False, indent=2), encoding="utf-8")


def _detect_source(air_path: Path, configured: str) -> str:
    metadata_path = air_path.with_suffix(".metadata.json")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return str(metadata.get("data_source", configured))
    return configured


def run_pipeline(config_path: Path, air_path: Path, weather_path: Path | None, output_dir: Path) -> dict:
    output_dir = Path(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = output_dir.parent / f".{output_dir.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        _run_pipeline(config_path, air_path, weather_path, staging)
        _write_json(staging / "run_manifest.json", {"status": "complete", "run_id": uuid.uuid4().hex})
        backup = None
        if output_dir.exists():
            backup = output_dir.parent / f".{output_dir.name}.backup-{uuid.uuid4().hex}"
            output_dir.rename(backup)
        staging.rename(output_dir)
        if backup is not None:
            shutil.rmtree(backup)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    figures = sorted((output_dir / "figures").glob("*.png"))
    return {"report": str(output_dir / "report.md"), "metrics": str(output_dir / "metrics.csv"), "figures": [str(path) for path in figures]}


def _run_pipeline(config_path: Path, air_path: Path, weather_path: Path | None, output_dir: Path) -> None:
    config = load_config(Path(config_path))
    air_path = Path(air_path)
    config["data_source"] = _detect_source(air_path, str(config["data_source"]))
    with (output_dir / "resolved_config.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)

    air = load_air_quality(air_path)
    weather = load_weather(Path(weather_path)) if weather_path else None
    clean, cleaning_log = prepare_hourly(air, weather)
    clean.to_csv(output_dir / "cleaned.csv", index=False)
    _write_json(output_dir / "cleaning_log.json", cleaning_log)
    featured, feature_columns = add_features(clean, config.get("heating_months"))
    stats = exploratory_analysis(featured, int(config["horizon"]), float(config["pm25_threshold"]), int(config.get("max_lag_hours", 48)))
    eda_dir = output_dir / "eda"
    eda_dir.mkdir(exist_ok=True)
    for name, table in stats.items():
        table.assign(data_source=config["data_source"]).to_csv(eda_dir / f"{name}.csv", index=True if name == "pollutant_correlation" else False)

    bundle = make_windows(
        featured, feature_columns, int(config["lookback"]), int(config["horizon"]),
        float(config["pm25_threshold"]), list(config["splits"]),
    )
    dataset_summary = {
        "data_source": config["data_source"], "feature_columns": feature_columns,
        "lookback": bundle.lookback, "horizon": bundle.horizon, "threshold": bundle.threshold,
        "purged": bundle.purged,
        "partitions": {
            name: {
                "samples": len(split.y), "positive": int(split.y.sum()), "negative": int(len(split.y) - split.y.sum()),
                "start": str(pd.Timestamp(split.timestamps[0])), "end": str(pd.Timestamp(split.timestamps[-1])),
            }
            for name, split in [("train", bundle.train), ("validation", bundle.val), ("test", bundle.test)]
        },
    }
    _write_json(output_dir / "dataset_summary.json", dataset_summary)
    (output_dir / "models").mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "sequence_scaler": bundle.sequence_scaler, "tabular_scaler": bundle.tabular_scaler,
        "feature_columns": bundle.feature_columns,
    }, output_dir / "models" / "preprocessing.joblib")
    results = train_all(bundle, config, output_dir)

    metric_rows = []
    prediction_frames = []
    model_details = {}
    for name, result in results.items():
        model_details[name] = {
            "validation": result.val_metrics, "test": result.metrics,
            "parameters": result.n_parameters, "training_seconds": result.training_seconds,
            "inference_seconds": result.inference_seconds, "feature_importances": result.feature_importances,
            "hardware": result.hardware,
        }
        for partition, metrics in [("validation", result.val_metrics), ("test", result.metrics)]:
            metric_rows.append({"model": name, "partition": partition, "data_source": config["data_source"], **metrics})
        for partition, split, scores in [("validation", bundle.val, result.val_scores), ("test", bundle.test, result.test_scores)]:
            prediction_frames.append(pd.DataFrame({
                "time": split.timestamps, "actual": split.y, "score": scores,
                "predicted": (scores >= result.threshold).astype(int), "current_pm25": split.current_pm25,
                "model": name, "partition": partition, "threshold": result.threshold,
                "data_source": config["data_source"],
            }))
    pd.DataFrame(metric_rows).to_csv(output_dir / "metrics.csv", index=False)
    pd.concat(prediction_frames, ignore_index=True).to_csv(output_dir / "predictions.csv", index=False)
    _write_json(output_dir / "metrics.json", {"data_source": config["data_source"], "models": model_details})
    generate_plots(featured, stats, cleaning_log, results, bundle, output_dir / "figures", config["data_source"])
    generate_report(output_dir)
