# 长春空气污染 XGBoost 短期预警研究

在原 SNN 研究方案基础上实现的可复现 Python 流水线，当前使用 XGBoost 替换 SNN。默认任务：使用过去 **48 小时**的污染与气象序列，预测未来 **6 小时**内 PM2.5 是否达到 **75 μg/m³**。该阈值是研究事件定义，不是官方公共预警标准。

包含数据质量检查、季节/滞后分析、无泄漏滑动窗口、持续性基线、逻辑回归、LSTM、XGBoost、时间外评估、特征重要性、核心图表和 Markdown 报告。

## Ubuntu Docker 部署（推荐）

笔记本已安装 Docker Engine 和 Docker Compose 插件时，无需单独安装 Python、Node.js 或 CUDA。将整个项目目录复制到 Ubuntu 后执行：

```bash
chmod +x scripts/install_ubuntu_docker.sh scripts/start_ubuntu_docker.sh
./scripts/install_ubuntu_docker.sh
./scripts/start_ubuntu_docker.sh
```

安装脚本会检查 Docker 并构建镜像；启动脚本会在后台启动服务并等待健康检查通过。前端和 API 均由同一个容器提供：

- 页面：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`

镜像使用 CPU 版 PyTorch。宿主机的 `data/` 和 `artifacts/` 会挂载到容器中，因此输入数据、新生成的配置和实验结果都会保留在项目目录。修改代码后重新运行安装脚本和启动脚本即可更新服务。

常用命令：

```bash
# 使用其他端口
AERISCOPE_PORT=8080 ./scripts/start_ubuntu_docker.sh

# 查看日志
docker compose logs -f app

# 停止服务
docker compose down

# 重新构建并启动
./scripts/install_ubuntu_docker.sh
./scripts/start_ubuntu_docker.sh
```

如果 Docker 已安装但当前用户没有权限，可先执行 `sudo systemctl enable --now docker`，再执行 `sudo usermod -aG docker $USER`，注销并重新登录后重试。

## 本地环境安装

推荐 Python 3.11。Windows 命令如下：

```bash
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m changchun_air.cli --help
```

Linux/macOS 将 `.venv/Scripts/python` 换成 `.venv/bin/python`。PyTorch 会按 pip 环境安装；若需要特定 CUDA 版本，请先按 PyTorch 官方说明安装，再执行本项目安装。

## 三分钟演示

```bash
.venv/Scripts/python -m changchun_air.cli demo-data --output data/demo/air_quality.csv --years 3 --seed 42
.venv/Scripts/python -m changchun_air.cli run --config configs/default.yaml --air data/demo/air_quality.csv --weather data/demo/weather.csv --output artifacts/demo
```

第一条命令同时生成 `air_quality.csv`、`weather.csv` 和来源元数据。**这些是合成数据，只用于验证软件流程，不能据此得出长春真实污染规律或模型优劣结论。** 配置中的 `data_source` 必须显式写为 `observed` 或 `synthetic`；若保留演示元数据，会自动识别为合成来源。复制演示 CSV 脱离元数据时，也必须把配置改为 `synthetic`。默认仅训练 3 轮以便快速演示；正式研究应复制配置并预先确定训练设置，而不是根据测试集结果调参。

每次运行先写入独立临时目录，全部成功后再替换目标产物；失败不会把部分新文件混入上一次成功结果。

主要结果：

- `artifacts/demo/report.md`：自动实验报告。
- `artifacts/demo/metrics.csv`：验证集和测试集指标。
- `artifacts/demo/predictions.csv`：每个模型的时间、分数和预测。
- `artifacts/demo/figures/`：8 张核心图。
- `artifacts/demo/models/`：逻辑回归与深度模型检查点。
- `artifacts/demo/resolved_config.yaml`：实际运行配置。
- `artifacts/demo/cleaning_log.json`、`dataset_summary.json`：质量与划分审计。

只根据固定结果重新生成报告：

```bash
.venv/Scripts/python -m changchun_air.cli report --output artifacts/demo
```

## 使用真实数据

### 1. 准备空气质量 CSV

从合法数据源下载长春城市级小时数据，保存为 UTF-8 或 GB18030 CSV。必须包含时间和 PM2.5；其他列可选：

```text
time,pm25,aqi,pm10,so2,no2,co,o3
2023-01-01 00:00:00,62,84,91,12,43,0.8,35
```

也支持 `日期/日期时间/时间`、`PM2.5`、`PM10`、`SO2`、`NO2`、`CO`、`O3` 等常见列名。时间按 `Asia/Shanghai` 本地小时解释；带时区时间会先转换到该时区。多站点数据请先自行统一为城市级或固定单站口径，不要混用。

### 2. 下载历史气象

```bash
.venv/Scripts/python -m changchun_air.cli download-weather --output data/raw/changchun_weather.csv --start 2021-01-01 --end 2023-12-31 --latitude 43.88 --longitude 125.35
```

使用 [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)，字段包括温度、相对湿度、10 米风速/风向、气压和降水。请自行确认数据许可、覆盖范围及再分析网格与站点观测的差异。

### 3. 运行实验

```bash
.venv/Scripts/python -m changchun_air.cli run --config configs/default.yaml --air data/raw/changchun_air.csv --weather data/raw/changchun_weather.csv --output artifacts/changchun
```

空气质量平台可能有访问限制，本项目不绕过限制，也不自动抓取；请手动合法下载。至少准备 2–3 个完整年度，最近时段留作最终测试。若某分区只有一种事件类别，程序会停止并提示调整研究时段或预先声明的阈值，不会复制或合成测试事件。

## 防泄漏与公平比较

- 空气质量与气象按小时精确对齐；重复时间取数值均值并记录，默认不插值。
- 滚动统计、变化率与滞后特征只使用当前和过去；输入及未来标签窗口必须连续完整。
- 训练/验证/测试按时间 60%/20%/20% 划分，边界清除可能跨区窗口。
- 标准化器只拟合训练数据；验证集选择最优检查点和 F1 决策阈值，测试集只作最终评估。
- LSTM 使用标准化序列；XGBoost 与逻辑回归使用相同的当前、滞后和滚动表格特征。XGBoost 默认 140 棵树、最大深度 4、学习率 0.05，并输出特征重要性。

## 修改实验配置

复制 `configs/default.yaml` 后修改 `lookback`、`horizon`、`pm25_threshold`、`xgb_estimators` 等，并通过 `--config` 传入。敏感性实验应分别保存到不同输出目录，预先报告所有设置，避免事后选择最优事件定义。

```bash
.venv/Scripts/python -m changchun_air.cli run --config configs/my_experiment.yaml --air data/raw/changchun_air.csv --weather data/raw/changchun_weather.csv --output artifacts/my_experiment
```

## AeriScope 高级研究前端

前端为 React + TypeScript，FastAPI 负责读取产物、计算 PR 曲线与误差案例、启动 Python 实验。数据处理、特征工程、模型训练和指标计算全部保留在 Python。

开发模式需要分别启动后端和前端：

```bash
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m changchun_air.web_api
```

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`。API 文档位于 `http://127.0.0.1:8000/docs`。

生产模式先构建前端，再启动后端；FastAPI 会直接托管构建结果：

```bash
cd frontend
npm run build
cd ..
.venv/Scripts/python -m changchun_air.web_api
```

访问 `http://127.0.0.1:8000`。页面包含研究总览、数据洞察、模型对照、XGBoost 实验室、情景推演、误差案例和实验运行七个视图。新实验产物保存在 `artifacts/web-runs/<run-id>`，支持明暗主题和移动端布局。

高级交互：模型页可拖动阈值并实时查看混淆矩阵；情景推演页通过 Python XGBoost 实时计算当前变量变化后的概率；数据页支持时间刷、快捷时间范围和气象同步缩放；`Ctrl+K` 可搜索页面与操作。情景推演只改变当前变量，属于模型敏感性分析，不是实际天气预报。

## 解释边界

统计关联和特征重要性不代表因果；历史样本外预测不等于识别污染机制。运行时间和树数量只用于实验内开销对照，不代表跨硬件的统一成本。本项目的输出是研究实验，不可直接用于现实公共预警。
