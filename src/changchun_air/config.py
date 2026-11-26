from pathlib import Path

import yaml


def load_config(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    required = {
        "seed", "lookback", "horizon", "pm25_threshold", "splits",
        "epochs", "batch_size", "learning_rate", "hidden_size", "xgb_estimators", "data_source",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"Missing configuration keys: {', '.join(missing)}")
    if config["data_source"] not in {"observed", "synthetic"}:
        raise ValueError("data_source must be explicitly set to 'observed' or 'synthetic'")
    if config["lookback"] < 1 or config["horizon"] < 1:
        raise ValueError("lookback and horizon must be positive")
    if len(config["splits"]) != 3 or abs(sum(config["splits"]) - 1.0) > 1e-8:
        raise ValueError("splits must contain three fractions summing to 1")
    return config
