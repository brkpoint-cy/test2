from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import precision_recall_curve

from .dataset import DatasetBundle
from .training import ModelResult

sns.set_theme(style="whitegrid")


def _save(fig: plt.Figure, output: Path, data_source: str) -> None:
    fig.text(0.99, 0.005, f"Data source: {data_source}", ha="right", fontsize=8, color="dimgray")
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_plots(
    frame: pd.DataFrame,
    stats: dict,
    cleaning_log: dict,
    results: dict[str, ModelResult],
    bundle: DatasetBundle,
    output_dir: Path,
    data_source: str,
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    missing = pd.Series(cleaning_log["missing_rates"]).sort_values(ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    missing.plot.bar(ax=ax, color="#56738c")
    ax.set(title="Missingness after hourly alignment", ylabel="Missing fraction", xlabel="")
    _save(fig, output_dir / "01_data_quality.png", data_source); paths.append(output_dir / "01_data_quality.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot(stats["monthly"]["month"], stats["monthly"]["mean"], marker="o")
    axes[0].set(title="Monthly mean PM2.5", xlabel="Month", ylabel="PM2.5 (ug/m3)", xticks=range(1, 13))
    sns.barplot(data=stats["heating_season"], x="heating_season", y="mean", ax=axes[1], color="#b7785d")
    axes[1].set(title="Heating-season comparison", xlabel="", ylabel="Mean PM2.5 (ug/m3)")
    _save(fig, output_dir / "02_seasonality.png", data_source); paths.append(output_dir / "02_seasonality.png")

    indexed = frame.set_index("time")
    daily = indexed["pm25"].resample("D").mean()
    peak_day = daily.idxmax()
    episode = indexed.loc[peak_day - pd.Timedelta(days=3):peak_day + pd.Timedelta(days=3)]
    variables = [c for c in ["pm25", "temperature", "humidity", "wind_speed"] if c in episode]
    fig, axes = plt.subplots(len(variables), 1, figsize=(11, 2.4 * len(variables)), sharex=True)
    if len(variables) == 1:
        axes = [axes]
    for ax, column in zip(axes, variables):
        ax.plot(episode.index, episode[column], linewidth=1)
        ax.set_ylabel(column)
    axes[0].set_title(f"Typical high-pollution episode around {peak_day.date()}")
    axes[-1].set_xlabel("Time")
    _save(fig, output_dir / "03_pollution_episode.png", data_source); paths.append(output_dir / "03_pollution_episode.png")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.heatmap(stats["pollutant_correlation"], annot=True, fmt=".2f", cmap="vlag", center=0, ax=axes[0])
    axes[0].set_title("Pollutant correlation (association, not causation)")
    lag = stats["lag_correlations"]
    if not lag.empty:
        pivot = lag.pivot(index="variable", columns="lag_hours", values="correlation")
        sns.heatmap(pivot, cmap="vlag", center=0, ax=axes[1])
        axes[1].set(title="Past meteorology vs current PM2.5", xlabel="Lag (hours)", ylabel="")
    _save(fig, output_dir / "04_correlations.png", data_source); paths.append(output_dir / "04_correlations.png")

    fig, ax = plt.subplots(figsize=(7, 6))
    for name, result in results.items():
        precision, recall, _ = precision_recall_curve(bundle.test.y, result.test_scores)
        ax.plot(recall, precision, label=f"{name} (AP={result.metrics['pr_auc']:.3f})")
    prevalence = float(np.mean(bundle.test.y))
    ax.axhline(prevalence, linestyle="--", color="grey", label=f"Prevalence={prevalence:.3f}")
    ax.set(title="Out-of-time test precision-recall curves", xlabel="Recall", ylabel="Precision", xlim=(0, 1), ylim=(0, 1.02))
    ax.legend(fontsize=8)
    _save(fig, output_dir / "05_model_pr_curves.png", data_source); paths.append(output_dir / "05_model_pr_curves.png")

    metrics = ["pr_auc", "recall", "precision", "f1", "false_alarm_rate"]
    x = np.arange(len(metrics))
    width = 0.8 / len(results)
    fig, ax = plt.subplots(figsize=(11, 5))
    for index, (name, result) in enumerate(results.items()):
        values = [result.metrics[metric] for metric in metrics]
        ax.bar(x + index * width, values, width, label=name)
    ax.set_xticks(x + width * (len(results) - 1) / 2, metrics)
    ax.set(title="Test metrics at validation-selected thresholds", ylabel="Score")
    ax.legend(fontsize=8)
    _save(fig, output_dir / "06_model_metrics.png", data_source); paths.append(output_dir / "06_model_metrics.png")

    xgboost = results["xgboost"]
    case_types = [("True positive / successful warning", (bundle.test.y == 1) & (xgboost.test_scores >= xgboost.threshold)),
                  ("False negative / missed event", (bundle.test.y == 1) & (xgboost.test_scores < xgboost.threshold)),
                  ("False positive / false alarm", (bundle.test.y == 0) & (xgboost.test_scores >= xgboost.threshold))]
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=False)
    for ax, (title, mask) in zip(axes, case_types):
        candidates = np.flatnonzero(mask)
        if not len(candidates):
            ax.text(0.5, 0.5, "No such case in the test period", ha="center", va="center")
            ax.set_title(title)
            continue
        index = int(candidates[0])
        timestamp = pd.Timestamp(bundle.test.timestamps[index])
        case = indexed.loc[timestamp - pd.Timedelta(hours=bundle.lookback):timestamp + pd.Timedelta(hours=bundle.horizon)]
        ax.plot(case.index, case["pm25"], label="PM2.5")
        ax.axvline(timestamp, color="black", linestyle="--", label="Forecast origin")
        ax.axhline(bundle.threshold, color="red", linestyle=":", label="Event threshold")
        ax.set_title(f"{title}: {timestamp}, score={xgboost.test_scores[index]:.3f}")
        ax.legend(fontsize=8)
    _save(fig, output_dir / "07_xgboost_error_cases.png", data_source); paths.append(output_dir / "07_xgboost_error_cases.png")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    importances = dict(list(xgboost.feature_importances.items())[:8])
    axes[0].barh(list(reversed(importances.keys())), list(reversed(importances.values())), color="#6b8e6f")
    axes[0].set(title="XGBoost feature importance", xlabel="Relative importance")
    names = list(results)
    times = [results[name].inference_seconds for name in names]
    axes[1].bar(names, times, color="#737f9e")
    axes[1].set(title="Measured test inference time", ylabel="Seconds")
    axes[1].tick_params(axis="x", rotation=25)
    _save(fig, output_dir / "08_xgboost_importance_runtime.png", data_source); paths.append(output_dir / "08_xgboost_importance_runtime.png")
    return paths
