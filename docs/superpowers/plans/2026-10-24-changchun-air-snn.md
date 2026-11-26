# 长春空气污染 SNN 预警项目 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建可复现的长春 PM2.5 短期预警研究流水线，完成数据清洗、探索分析、四模型公平比较、图表和报告。

**Architecture:** `src` 布局的配置化 Python 包。数据层输出按小时对齐的表，样本层输出无泄漏窗口与划分，模型层统一产生验证/测试分数，评估和报告层只消费固定结果。

**Tech Stack:** Python 3.11、NumPy、pandas、scikit-learn、PyTorch、snnTorch、Matplotlib、seaborn、PyYAML、requests、joblib。

**Spec:** `docs/superpowers/specs/2026-10-24-changchun-air-snn-design.md`

## Global Constraints

- 默认过去 48 小时预测未来 6 小时，PM2.5 事件阈值为 75 μg/m³。
- 默认不插值，不使用未来数据构造特征、标签、标准化或阈值。
- 时间顺序 60%/20%/20% 划分，边界清除重叠窗口；每区必须有正负样本。
- 深度模型输入、划分和训练轮数一致；验证集选检查点与 F1 阈值，测试集只最终评估。
- 合成结果始终标注 `synthetic`，不得写成真实长春观测结论或实际节能结论。
- 项目无既有测试体系，不新增测试目录；使用内联断言与真实 CLI 端到端运行验证。
- 当前不是 Git 仓库，不执行 `git init` 或提交。

## Review Focus

- 缺列、非法时间或非数值 PM2.5：导入应指出具体字段/行问题，由 `load_air_quality` 的冒烟输入验证。
- 重复时间与小时缺口：不得静默模糊匹配，由清洗日志及连续窗口断言验证。
- 单类别分区：应明确报错，由小样本划分断言验证。
- 空预测或单类别评估：PR-AUC 等指标不得悄悄填 0，由评估输入检查验证。
- 演示与真实数据混淆：所有指标和报告必须携带来源标记，由最终产物断言验证。

---

### Task 1: 项目骨架、配置与数据获取

**Files:**
- Create: `pyproject.toml`、`requirements.txt`、`.gitignore`、`configs/default.yaml`
- Create: `src/changchun_air/__init__.py`、`config.py`、`data.py`、`cli.py`

**Interfaces:**
- Produces: `load_config(path: Path) -> dict`、`make_demo_data(output: Path, years: int, seed: int) -> pd.DataFrame`。
- Produces: `load_air_quality(path: Path) -> pd.DataFrame`、`load_weather(path: Path) -> pd.DataFrame`。
- Produces: `download_weather(output: Path, start: str, end: str, latitude: float, longitude: float) -> pd.DataFrame`。
- CLI: `demo-data`、`download-weather`、`run`、`report`。

- [ ] **Step 1: 写配置与依赖**

配置包含 `seed: 42`、`lookback: 48`、`horizon: 6`、`pm25_threshold: 75.0`、`splits: [0.6, 0.2, 0.2]`、`snn_steps: 12`、`epochs`、`batch_size`、`learning_rate` 和 `hidden_size`。依赖版本只设兼容下限，不伪造锁定环境。

- [ ] **Step 2: 实现严格数据接口**

列别名至少覆盖 `time/日期/日期时间`、`pm25/PM2.5`、`aqi/AQI`、`pm10/PM10`、`so2/SO2`、`no2/NO2`、`co/CO`、`o3/O3`。时间解析为小时本地时间，保留原始缺失，负数污染值转为缺失并计数。Open-Meteo 请求 `temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation`，参数 `timezone=Asia/Shanghai`，非 200 响应抛出包含状态码的错误。

- [ ] **Step 3: 实现固定种子合成数据**

用 NumPy 生成器构造 3 年小时序列：冬季基线、日周期、AR(1) 污染过程、温湿风相关扰动，PM2.5 截断为非负。同期生成其他污染物和气象字段，输出 `data_source=synthetic` 元数据，不插入影响默认完整流程的随机缺失。

- [ ] **Step 4: 冒烟验证**

运行：

```bash
py -3.11 -m venv --system-site-packages .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m changchun_air.cli --help
.venv/Scripts/python -m changchun_air.cli demo-data --output data/demo/air_quality.csv --years 3
.venv/Scripts/python -m changchun_air.cli download-weather --output data/demo/weather_download.csv --start 2024-01-01 --end 2024-01-03
```

预期：CLI 四个命令可见，演示数据时间连续且 PM2.5 非负，下载表有 72 行和所请求气象字段。

### Task 2: 清洗、探索分析与无泄漏样本

**Files:**
- Create: `src/changchun_air/preprocessing.py`、`features.py`、`dataset.py`
- Create: `src/changchun_air/eda.py`

**Interfaces:**
- Consumes: Task 1 的两个加载器。
- Produces: `prepare_hourly(air: pd.DataFrame, weather: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]`。
- Produces: `add_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]`。
- Produces: `make_windows(frame, feature_columns, lookback, horizon, threshold, splits) -> DatasetBundle`。
- `DatasetBundle` 含 `train/val/test`，每区含 `X: np.ndarray`、`tabular: np.ndarray`、`y: np.ndarray`、`timestamps: np.ndarray`、`current_pm25: np.ndarray`。

- [ ] **Step 1: 实现清洗与日志**

精确按 `time` 外连接空气质量与气象，随后按小时重索引以暴露缺口；日志记录重复、缺失、保留行、起止时间和连续缺失长度分布。默认不填充；输出 `cleaned.csv` 与 `cleaning_log.json`。

- [ ] **Step 2: 实现过去向特征**

对 PM2.5 构造 `lag_1/lag_3/lag_6/lag_12/lag_24`、`rolling_mean_6/24`、`rolling_max_6/24`、`change_1/6/24`；滚动只用 `rolling(..., min_periods=窗口)`。添加小时、星期、月份正余弦、采暖季与风向正余弦。

- [ ] **Step 3: 实现窗口与隔离边界**

仅当输入 `lookback` 和未来 `horizon` 的所有小时连续、PM2.5 和特征完整时生成样本。`y = max(pm25[t+1:t+h+1]) >= threshold`。排序后按比例分区，并在训练/验证与验证/测试边界各删除 `lookback + horizon - 1` 个靠后分区的起始样本，记录清除量。`StandardScaler` 只 `fit(train.X.reshape(-1, n_features))`；表格特征只用训练区拟合另一标准化器。

- [ ] **Step 4: 实现探索统计**

输出月度与采暖季汇总、污染物相关矩阵、气象与 PM2.5 的 0–48 小时滞后相关、事件持续时间和类别比例。气象滞后使用 `meteorology.shift(lag).corr(pm25)`，明确只是关联。

- [ ] **Step 5: 内联冒烟断言**

用 200 小时手工序列验证：窗口时间戳与末端一致、输入末值等于当前值、未来标签阈值正确、跨缺口窗口被排除、边界时间范围不重叠、 scaler 的拟合样本数只等于训练窗口元素数。用单类别小数据调用划分并预期 `ValueError`。

### Task 3: 四模型、阈值选择与统一评估

**Files:**
- Create: `src/changchun_air/models.py`、`training.py`、`evaluation.py`

**Interfaces:**
- Consumes: `DatasetBundle` 和配置字典。
- Produces: `train_all(bundle, config, output_dir) -> dict[str, ModelResult]`。
- `ModelResult` 含验证/测试概率、阈值、指标、参数量、训练/推理秒数及 SNN 分层脉冲率。
- Produces: `binary_metrics(y, score, threshold) -> dict`、`select_f1_threshold(y, score) -> float`。

- [ ] **Step 1: 实现基线与逻辑回归**

持续性分数为 `(current_pm25 >= threshold).astype(float)`。逻辑回归 `class_weight="balanced"`、`max_iter=1000`、固定种子，使用训练表格特征，保存 joblib。两模型与深度模型共享相同阈值选择函数。

- [ ] **Step 2: 实现 LSTM 与 SNN**

`LSTMClassifier` 使用单层 LSTM 和最后一个隐状态；`SNNClassifier` 使用 `Linear -> snntorch.Leaky -> Linear -> Leaky -> Linear`，每个模拟步重复相同输入向量并累计输出膜电位。`forward` 返回 logits 与分层脉冲率，脉冲率用总脉冲数/神经元元素数。

- [ ] **Step 3: 实现可复现训练**

设置 Python、NumPy、Torch 种子；`BCEWithLogitsLoss(pos_weight=负例数/正例数)`。每轮仅在训练加载器打乱；按验证 PR-AUC 保存最优 state dict，最后恢复。阈值从验证预测候选分位点中选择最大 F1，并列取更保守（较高）阈值。记录 `platform.processor()`、Torch 设备、参数量与耗时。

- [ ] **Step 4: 实现指标与预测文件**

指标含 PR-AUC、ROC-AUC、Precision、Recall、F1、FAR、Accuracy、TN/FP/FN/TP、正负支持数。无正例时 PR-AUC 返回 `NaN` 并在汇总标记，无负例时 ROC-AUC/FAR 返回 `NaN`，不静默变成 0。CSV 含时间、真实值、分数、预测、当前 PM2.5、模型、分区和数据来源。

- [ ] **Step 5: 小网络冒烟验证**

用 256 个可分的合成窗口各训练 1 轮，验证输出形状、有限概率、检查点恢复、阈值仅由验证分数计算、SNN 脉冲率在 `[0,1]`。用全负标签确认 ROC-AUC 为 `NaN`。

### Task 4: 可视化、报告与完整流水线

**Files:**
- Create: `src/changchun_air/plots.py`、`reporting.py`、`pipeline.py`
- Modify: `src/changchun_air/cli.py`
- Create: `README.md`

**Interfaces:**
- Consumes: 清洗表、EDA 统计、四个 `ModelResult`。
- Produces: `run_pipeline(config_path: Path, air_path: Path, weather_path: Path | None, output_dir: Path) -> dict`。
- Produces: `generate_report(output_dir: Path) -> Path`。
- 产物：`metrics.json/csv`、`predictions.csv`、`figures/*.png`、`report.md`、`resolved_config.yaml`。

- [ ] **Step 1: 实现核心图表**

统一无交互后端与字体降级，生成数据质量、月度/采暖季、典型污染过程、相关/滞后、四模型 PR 曲线、指标对比、SNN 稀疏性与耗时。典型案例从测试预测选 TP/FN/FP 各一个，绘制前后 48 小时序列；案例不存在时在图题明确“测试期无此案例”，不伪造。

- [ ] **Step 2: 实现报告生成**

报告包含数据来源醒目标记、时间范围、窗口与阈值、分区支持数、模型指标表、开销/脉冲率、图表相对链接和结果边界。若来源为合成数据，开头写“以下结果仅验证软件流程，不是长春真实空气质量研究结论”。

- [ ] **Step 3: 串联原子化输出**

每个运行写入独立目录；先创建目录，再保存解析后的配置。任何阶段失败保留错误并停止，不写成功报告。完成后输出指标与报告路径。`report` 仅从已有机器可读产物重生成报告。

- [ ] **Step 4: 编写使用文档**

README 包含 Python 3.11 安装、三分钟演示、真实 CSV 格式、气象下载、完整运行、配置副本修改方法、产物说明和研究边界。真实数据示例使用用户本地路径，不宣称随仓库附带真实观测。

- [ ] **Step 5: 编译与命令检查**

运行 `.venv/Scripts/python -m compileall -q src` 和四个 CLI 的 `--help`，预期退出码 0。

### Task 5: 端到端验证与交付审查

**Files:**
- Verify: 上述全部文件和 `artifacts/demo/`
- Modify if needed: 仅修复验证发现的实际缺陷。

- [ ] **Step 1: 运行完整演示**

```bash
.venv/Scripts/python -m changchun_air.cli run --config configs/default.yaml --air data/demo/air_quality.csv --weather data/demo/weather.csv --output artifacts/demo
```

预期：四个模型均训练并完成最终测试评估，退出码 0。

- [ ] **Step 2: 验证交付物和研究约束**

内联 Python 断言检查：指标包含四模型；每模型测试预测数相同；时间严格有序；所有概率有限且在 `[0,1]`；阈值与验证选择结果一致；至少六个 PNG 非空；报告含 `synthetic`、窗口、阈值和局限性；配置种子与解析配置一致。

- [ ] **Step 3: 检查真实数据入口**

运行 Task 1 的真实 Open-Meteo 下载并用空气质量加载器读取一个手工构造的短 CSV，确认中英文字段映射与非法字段报错。说明真实空气数据尚未提供，因此不声称已得到真实研究结论。

- [ ] **Step 4: 最终质量审查**

搜索空 `except`、`TODO`、未来向 `rolling`/`bfill`、随机划分和夸大措辞；检查 README 命令与实际 CLI 一致。重新运行编译和完整演示关键检查，记录任何未能验证的项目。
