import json
import platform
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from torch.utils.data import DataLoader, TensorDataset
from xgboost import XGBClassifier

from .dataset import DatasetBundle, Split
from .evaluation import binary_metrics, select_f1_threshold
from .models import LSTMClassifier


@dataclass
class ModelResult:
    model: str
    val_scores: np.ndarray
    test_scores: np.ndarray
    threshold: float
    val_metrics: dict
    metrics: dict
    n_parameters: int
    training_seconds: float
    inference_seconds: float
    feature_importances: dict[str, float] = field(default_factory=dict)
    hardware: dict[str, str] = field(default_factory=dict)


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _result(name: str, bundle: DatasetBundle, val_scores: np.ndarray, test_scores: np.ndarray, **details) -> ModelResult:
    threshold = select_f1_threshold(bundle.val.y, val_scores)
    return ModelResult(
        model=name, val_scores=val_scores, test_scores=test_scores, threshold=threshold,
        val_metrics=binary_metrics(bundle.val.y, val_scores, threshold),
        metrics=binary_metrics(bundle.test.y, test_scores, threshold), **details,
    )


def _predict_deep(model: torch.nn.Module, split: Split, batch_size: int, device: torch.device) -> tuple[np.ndarray, dict[str, float]]:
    loader = DataLoader(TensorDataset(torch.from_numpy(split.X)), batch_size=batch_size, shuffle=False)
    scores = []
    spike_totals: dict[str, float] = {}
    model.eval()
    with torch.no_grad():
        for (X,) in loader:
            logits, rates = model(X.to(device))
            scores.append(torch.sigmoid(logits).cpu().numpy())
            for layer, value in rates.items():
                spike_totals[layer] = spike_totals.get(layer, 0.0) + value * len(X)
    rates = {layer: value / len(split.X) for layer, value in spike_totals.items()}
    return np.concatenate(scores), rates


def _train_deep(name: str, model: torch.nn.Module, bundle: DatasetBundle, config: dict, output_dir: Path) -> ModelResult:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    batch_size = int(config["batch_size"])
    generator = torch.Generator().manual_seed(int(config["seed"]))
    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(bundle.train.X), torch.from_numpy(bundle.train.y.astype(np.float32))),
        batch_size=batch_size, shuffle=True, generator=generator,
    )
    positives = float(bundle.train.y.sum())
    negatives = float(len(bundle.train.y) - positives)
    loss_function = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negatives / positives, device=device))
    optimizer = torch.optim.Adam(model.parameters(), lr=float(config["learning_rate"]))
    best_score = -np.inf
    best_state = None
    model_dir = Path(output_dir) / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    for _ in range(int(config["epochs"])):
        model.train()
        for X, y in train_loader:
            optimizer.zero_grad()
            logits, _ = model(X.to(device))
            loss = loss_function(logits, y.to(device))
            loss.backward()
            optimizer.step()
        val_scores, _ = _predict_deep(model, bundle.val, batch_size, device)
        val_pr_auc = average_precision_score(bundle.val.y, val_scores)
        if val_pr_auc > best_score:
            best_score = val_pr_auc
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    training_seconds = time.perf_counter() - start
    if best_state is None:
        raise RuntimeError(f"{name} training produced no checkpoint")
    model.load_state_dict(best_state)
    torch.save({"model_state": best_state, "validation_pr_auc": best_score}, model_dir / f"{name}.pt")
    val_scores, _ = _predict_deep(model, bundle.val, batch_size, device)
    inference_start = time.perf_counter()
    test_scores, _ = _predict_deep(model, bundle.test, batch_size, device)
    inference_seconds = time.perf_counter() - inference_start
    return _result(
        name, bundle, val_scores, test_scores,
        n_parameters=sum(parameter.numel() for parameter in model.parameters()),
        training_seconds=training_seconds, inference_seconds=inference_seconds,
        hardware={"device": str(device), "processor": platform.processor() or platform.machine(), "torch": torch.__version__},
    )


def train_all(bundle: DatasetBundle, config: dict, output_dir: Path) -> dict[str, ModelResult]:
    _seed_everything(int(config["seed"]))
    output_dir = Path(output_dir)
    (output_dir / "models").mkdir(parents=True, exist_ok=True)
    results = {}
    persistence_start = time.perf_counter()
    persistence_val = (bundle.val.current_pm25 >= bundle.threshold).astype(float)
    persistence_test = (bundle.test.current_pm25 >= bundle.threshold).astype(float)
    results["persistence"] = _result(
        "persistence", bundle, persistence_val, persistence_test,
        n_parameters=0, training_seconds=0.0,
        inference_seconds=time.perf_counter() - persistence_start,
        hardware={"device": "cpu", "processor": platform.processor() or platform.machine()},
    )
    logistic = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=int(config["seed"]))
    logistic_start = time.perf_counter()
    logistic.fit(bundle.train.tabular, bundle.train.y)
    logistic_training = time.perf_counter() - logistic_start
    joblib.dump(logistic, output_dir / "models" / "logistic_regression.joblib")
    val_scores = logistic.predict_proba(bundle.val.tabular)[:, 1]
    inference_start = time.perf_counter()
    test_scores = logistic.predict_proba(bundle.test.tabular)[:, 1]
    results["logistic_regression"] = _result(
        "logistic_regression", bundle, val_scores, test_scores,
        n_parameters=int(logistic.coef_.size + logistic.intercept_.size),
        training_seconds=logistic_training, inference_seconds=time.perf_counter() - inference_start,
        hardware={"device": "cpu", "processor": platform.processor() or platform.machine()},
    )
    n_features = len(bundle.feature_columns)
    lstm = LSTMClassifier(n_features, int(config["hidden_size"]))
    results["lstm"] = _train_deep("lstm", lstm, bundle, config, output_dir)
    positives = float(bundle.train.y.sum())
    negatives = float(len(bundle.train.y) - positives)
    xgboost = XGBClassifier(
        n_estimators=int(config["xgb_estimators"]), max_depth=int(config.get("xgb_max_depth", 4)),
        learning_rate=float(config.get("xgb_learning_rate", 0.05)), subsample=0.85,
        colsample_bytree=0.85, eval_metric="logloss", random_state=int(config["seed"]),
        n_jobs=4, scale_pos_weight=negatives / positives,
    )
    xgb_start = time.perf_counter()
    xgboost.fit(bundle.train.tabular, bundle.train.y)
    xgb_training = time.perf_counter() - xgb_start
    joblib.dump(xgboost, output_dir / "models" / "xgboost.joblib")
    val_scores = xgboost.predict_proba(bundle.val.tabular)[:, 1]
    inference_start = time.perf_counter()
    test_scores = xgboost.predict_proba(bundle.test.tabular)[:, 1]
    importances = dict(zip(bundle.feature_columns, xgboost.feature_importances_.tolist()))
    importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True)[:12])
    results["xgboost"] = _result(
        "xgboost", bundle, val_scores, test_scores,
        n_parameters=int(xgboost.get_booster().num_boosted_rounds()),
        training_seconds=xgb_training, inference_seconds=time.perf_counter() - inference_start,
        feature_importances=importances,
        hardware={"device": "cpu", "processor": platform.processor() or platform.machine()},
    )
    return results
