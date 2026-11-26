import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sklearn.metrics import precision_recall_curve

from .config import load_config
from .features import add_features
from .pipeline import run_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = PROJECT_ROOT / "artifacts" / "demo"
app = FastAPI(title="AeriScope API", version="1.0.0")


def _json_value(value):
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_value(item) for item in value]
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


class ArtifactSnapshot:
    def __init__(self, root: Path):
        self.root = root

    def path(self, name: str) -> Path:
        path = self.root / name
        if not path.is_file():
            raise HTTPException(status_code=503, detail=f"研究产物尚未生成：{name}")
        return path

    def json(self, name: str):
        try:
            return json.loads(self.path(name).read_text(encoding="utf-8"))
        except HTTPException:
            raise
        except (OSError, ValueError, TypeError) as exc:
            raise HTTPException(status_code=503, detail=f"研究产物无法解析：{name}") from exc

    def yaml(self, name: str):
        try:
            return yaml.safe_load(self.path(name).read_text(encoding="utf-8"))
        except HTTPException:
            raise
        except (OSError, yaml.YAMLError) as exc:
            raise HTTPException(status_code=503, detail=f"研究配置无法解析：{name}") from exc

    def csv(self, name: str) -> pd.DataFrame:
        try:
            return pd.read_csv(self.path(name))
        except HTTPException:
            raise
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            raise HTTPException(status_code=503, detail=f"研究数据无法解析：{name}") from exc

    def source(self) -> str:
        source = self.json("metrics.json").get("data_source")
        if source not in {"observed", "synthetic"}:
            raise HTTPException(status_code=503, detail="研究产物缺少有效的数据来源标记")
        return source


class ArtifactStore:
    def __init__(self):
        self.current = DEFAULT_ARTIFACT
        self.lock = threading.Lock()

    def snapshot(self) -> ArtifactSnapshot:
        with self.lock:
            return ArtifactSnapshot(self.current)

    def publish(self, root: Path) -> None:
        with self.lock:
            self.current = root


store = ArtifactStore()


def _models(artifacts: ArtifactSnapshot) -> list[dict]:
    details = artifacts.json("metrics.json").get("models")
    required = {"persistence", "logistic_regression", "lstm", "xgboost"}
    if not isinstance(details, dict) or not required.issubset(details):
        raise HTTPException(status_code=503, detail="研究产物缺少完整的四模型结果")
    for name in required:
        if not {"validation", "test"}.issubset(details[name]):
            raise HTTPException(status_code=503, detail=f"模型 {name} 缺少验证或测试指标")
    return [{"name": name, **details[name]} for name in ["persistence", "logistic_regression", "lstm", "xgboost"]]


def _records(frame: pd.DataFrame) -> list[dict]:
    return _json_value(frame.to_dict(orient="records"))


class ExperimentRequest(BaseModel):
    air_path: str = "data/demo/air_quality.csv"
    weather_path: str | None = "data/demo/weather.csv"
    data_source: str = Field(default="synthetic", pattern="^(observed|synthetic)$")
    lookback: int = Field(default=48, ge=6, le=168)
    horizon: int = Field(default=6, ge=1, le=48)
    pm25_threshold: float = Field(default=75, gt=0, le=500)
    epochs: int = Field(default=3, ge=1, le=50)
    xgb_estimators: int = Field(default=140, ge=20, le=500)


class SimulationRequest(BaseModel):
    sample_index: int = Field(ge=0)
    pm25: float = Field(ge=0, le=500)
    temperature: float = Field(ge=-50, le=60)
    humidity: float = Field(ge=0, le=100)
    wind_speed: float = Field(ge=0, le=50)


class ExperimentManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.lock = threading.Lock()
        self.state = {"run_id": None, "status": "idle", "message": "等待运行", "output": None}

    def snapshot(self) -> dict:
        with self.lock:
            state = dict(self.state)
        try:
            state["data_source"] = store.snapshot().source()
        except HTTPException:
            state["data_source"] = None
        return state

    def start(self, request: ExperimentRequest) -> dict:
        with self.lock:
            if self.state["status"] in {"queued", "running"}:
                raise HTTPException(status_code=409, detail="已有实验正在运行，请等待完成")
            run_id = uuid.uuid4().hex[:12]
            self.state = {"run_id": run_id, "status": "queued", "message": "实验已进入队列", "output": None}
        self.executor.submit(self._execute, run_id, request)
        return self.snapshot()

    def _project_file(self, value: str) -> Path:
        path = (PROJECT_ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
        if PROJECT_ROOT not in path.parents and path != PROJECT_ROOT:
            raise ValueError("数据文件必须位于项目目录内")
        if not path.is_file():
            raise ValueError(f"数据文件不存在：{value}")
        return path

    def _execute(self, run_id: str, request: ExperimentRequest):
        try:
            with self.lock:
                self.state.update(status="running", message="Python 正在清洗数据并训练四类模型")
            air = self._project_file(request.air_path)
            weather = self._project_file(request.weather_path) if request.weather_path else None
            config = load_config(PROJECT_ROOT / "configs" / "default.yaml")
            config.update(request.model_dump(exclude={"air_path", "weather_path"}))
            config_dir = PROJECT_ROOT / "artifacts" / "web-configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f"{run_id}.yaml"
            config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
            output = PROJECT_ROOT / "artifacts" / "web-runs" / run_id
            run_pipeline(config_path, air, weather, output)
            store.publish(output)
            with self.lock:
                self.state.update(status="complete", message="实验完成，结果已发布", output=str(output.relative_to(PROJECT_ROOT)))
        except Exception as exc:
            with self.lock:
                self.state.update(status="failed", message=str(exc))


experiments = ExperimentManager()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AeriScope", "python_ml": True}


@app.get("/api/dashboard")
def dashboard():
    artifacts = store.snapshot()
    dataset = artifacts.json("dataset_summary.json")
    if "test" not in dataset.get("partitions", {}):
        raise HTTPException(status_code=503, detail="研究产物缺少测试分区")
    return _json_value({
        "data_source": artifacts.source(),
        "config": artifacts.yaml("resolved_config.yaml"),
        "cleaning": artifacts.json("cleaning_log.json"),
        "dataset": dataset,
        "models": _models(artifacts),
        "monthly": _records(artifacts.csv("eda/monthly.csv")),
        "events": _records(artifacts.csv("eda/event_stats.csv")),
        "run": experiments.snapshot(),
    })


@app.get("/api/eda")
def eda():
    artifacts = store.snapshot()
    clean = artifacts.csv("cleaned.csv")
    if len(clean) > 1600:
        clean = clean.iloc[np.linspace(0, len(clean) - 1, 1600).astype(int)]
    columns = ["time", "pm25", "temperature", "wind_speed"]
    columns = [column for column in columns if column in clean]
    if not {"time", "pm25"}.issubset(columns):
        raise HTTPException(status_code=503, detail="清洗数据缺少 time 或 pm25")
    return _json_value({
        "data_source": artifacts.source(),
        "missing": artifacts.json("cleaning_log.json")["missing_rates"],
        "monthly": _records(artifacts.csv("eda/monthly.csv")),
        "heating": _records(artifacts.csv("eda/heating_season.csv")),
        "lags": _records(artifacts.csv("eda/lag_correlations.csv")),
        "events": _records(artifacts.csv("eda/event_stats.csv")),
        "series": _records(clean[columns]),
    })


@app.get("/api/models")
def models():
    artifacts = store.snapshot()
    model_results = _models(artifacts)
    predictions = artifacts.csv("predictions.csv")
    if not {"model", "partition", "actual", "score"}.issubset(predictions.columns):
        raise HTTPException(status_code=503, detail="预测明细缺少必要字段")
    curves = {}
    for name in [item["name"] for item in model_results]:
        test = predictions[(predictions["model"] == name) & (predictions["partition"] == "test")]
        if test.empty:
            raise HTTPException(status_code=503, detail=f"模型 {name} 没有测试预测")
        precision, recall, _ = precision_recall_curve(test["actual"], test["score"])
        indices = np.linspace(0, len(precision) - 1, min(240, len(precision))).astype(int)
        curves[name] = [{"precision": precision[i], "recall": recall[i]} for i in indices]
    return _json_value({"data_source": artifacts.source(), "models": model_results, "curves": curves})


@app.get("/api/cases")
def cases(model: str = Query(default="xgboost")):
    artifacts = store.snapshot()
    config = artifacts.yaml("resolved_config.yaml")
    predictions = artifacts.csv("predictions.csv")
    selected = predictions[(predictions["model"] == model) & (predictions["partition"] == "test")].copy()
    if selected.empty:
        raise HTTPException(status_code=404, detail=f"未知模型或没有测试预测：{model}")
    selected["time"] = pd.to_datetime(selected["time"])
    clean = artifacts.csv("cleaned.csv")
    clean["time"] = pd.to_datetime(clean["time"])
    clean = clean.set_index("time")
    decision_threshold = float(selected["threshold"].iloc[0])
    kinds = {
        "tp": ("成功预警", (selected["actual"] == 1) & (selected["predicted"] == 1)),
        "fn": ("漏报事件", (selected["actual"] == 1) & (selected["predicted"] == 0)),
        "fp": ("误报警报", (selected["actual"] == 0) & (selected["predicted"] == 1)),
    }
    response = {}
    horizon = int(config["horizon"])
    lookback = int(config["lookback"])
    for key, (label, mask) in kinds.items():
        candidates = selected[mask]
        if candidates.empty:
            response[key] = {"label": label, "available": False, "series": []}
            continue
        row = candidates.iloc[0]
        timestamp = row["time"]
        context = clean.loc[timestamp - pd.Timedelta(hours=lookback):timestamp + pd.Timedelta(hours=horizon)].reset_index()
        series = [{"time": item.time, "pm25": item.pm25, "phase": "future" if item.time > timestamp else "history"} for item in context.itertuples()]
        response[key] = {
            "label": label, "available": True, "time": timestamp, "score": row["score"],
            "actual": int(row["actual"]), "threshold": decision_threshold, "series": series,
        }
    return _json_value({
        "data_source": artifacts.source(), "model": model, "cases": response,
        "pm25_threshold": float(config["pm25_threshold"]), "lookback": lookback, "horizon": horizon,
    })


@app.get("/api/threshold-analysis")
def threshold_analysis(model: str = Query(default="xgboost"), partition: str = Query(default="test")):
    if partition not in {"validation", "test"}:
        raise HTTPException(status_code=400, detail="partition 必须是 validation 或 test")
    artifacts = store.snapshot()
    predictions = artifacts.csv("predictions.csv")
    selected = predictions[(predictions["model"] == model) & (predictions["partition"] == partition)]
    if selected.empty:
        raise HTTPException(status_code=404, detail="没有可用于阈值分析的预测")
    y = selected["actual"].to_numpy(dtype=int)
    scores = selected["score"].to_numpy(dtype=float)
    points = []
    for threshold in np.linspace(0, 1, 101):
        predicted = (scores >= threshold).astype(int)
        tn = int(np.sum((y == 0) & (predicted == 0)))
        fp = int(np.sum((y == 0) & (predicted == 1)))
        fn = int(np.sum((y == 1) & (predicted == 0)))
        tp = int(np.sum((y == 1) & (predicted == 1)))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        points.append({
            "threshold": float(threshold), "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
            "accuracy": (tp + tn) / len(y), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        })
    return _json_value({
        "data_source": artifacts.source(), "model": model, "partition": partition,
        "validation_threshold": float(selected["threshold"].iloc[0]), "points": points,
    })


def _simulation_context(artifacts: ArtifactSnapshot, sample_index: int):
    predictions = artifacts.csv("predictions.csv")
    selected = predictions[(predictions["model"] == "xgboost") & (predictions["partition"] == "test")].reset_index(drop=True)
    if sample_index >= len(selected):
        raise HTTPException(status_code=404, detail="情景样本索引超出测试集范围")
    clean = artifacts.csv("cleaned.csv")
    clean["time"] = pd.to_datetime(clean["time"])
    featured, _ = add_features(clean)
    prediction = selected.iloc[sample_index]
    timestamp = pd.Timestamp(prediction["time"])
    rows = featured.index[featured["time"].eq(timestamp)]
    if rows.empty:
        raise HTTPException(status_code=503, detail="找不到情景样本对应的特征行")
    row = featured.loc[rows[0]].copy()
    preprocessing = joblib.load(artifacts.path("models/preprocessing.joblib"))
    model = joblib.load(artifacts.path("models/xgboost.joblib"))
    columns = preprocessing["feature_columns"]
    if row[columns].isna().any():
        raise HTTPException(status_code=503, detail="情景样本特征不完整")
    scaled = preprocessing["tabular_scaler"].transform(row[columns].to_frame().T)
    baseline = float(model.predict_proba(scaled)[:, 1][0])
    return {
        "data_source": artifacts.source(), "sample_index": sample_index, "sample_count": len(selected),
        "time": timestamp, "actual": int(prediction["actual"]), "threshold": float(prediction["threshold"]),
        "baseline_score": baseline, "row": row, "model": model,
        "scaler": preprocessing["tabular_scaler"], "feature_columns": columns,
    }


@app.get("/api/simulation-context")
def simulation_context(sample_index: int = Query(default=0, ge=0)):
    artifacts = store.snapshot()
    context = _simulation_context(artifacts, sample_index)
    row = context.pop("row")
    context.pop("model")
    context.pop("scaler")
    context.pop("feature_columns")
    return _json_value({**context, "values": {
        "pm25": row["pm25"], "temperature": row.get("temperature", 0),
        "humidity": row.get("humidity", 50), "wind_speed": row.get("wind_speed", 0),
    }})


@app.post("/api/simulate")
def simulate(request: SimulationRequest):
    artifacts = store.snapshot()
    context = _simulation_context(artifacts, request.sample_index)
    row = context.pop("row")
    model = context.pop("model")
    scaler = context.pop("scaler")
    columns = context.pop("feature_columns")
    for column in ["pm25", "temperature", "humidity", "wind_speed"]:
        if column not in row:
            raise HTTPException(status_code=503, detail=f"当前实验缺少情景变量：{column}")
        row[column] = getattr(request, column)
    scaled = scaler.transform(row[columns].to_frame().T)
    score = float(model.predict_proba(scaled)[:, 1][0])
    return _json_value({**context, "score": score, "delta": score - context["baseline_score"],
                        "predicted": int(score >= context["threshold"])})


@app.get("/api/report")
def report():
    return FileResponse(store.snapshot().path("report.md"), media_type="text/markdown", filename="aeriscope-report.md")


@app.get("/api/figures/{name}")
def figure(name: str):
    if Path(name).name != name or not name.endswith(".png"):
        raise HTTPException(status_code=400, detail="非法图表名称")
    return FileResponse(store.snapshot().path(f"figures/{name}"))


@app.get("/api/experiments")
def experiment_status():
    return experiments.snapshot()


@app.post("/api/experiments", status_code=202)
def start_experiment(request: ExperimentRequest):
    return experiments.start(request)


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if FRONTEND_DIST.exists():
        requested = (FRONTEND_DIST / path).resolve()
        if path and FRONTEND_DIST in requested.parents and requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")
    return {"message": "AeriScope API 正在运行。前端开发服务器请使用 npm run dev。"}


if __name__ == "__main__":
    uvicorn.run("changchun_air.web_api:app", host="127.0.0.1", port=8000, reload=False)
