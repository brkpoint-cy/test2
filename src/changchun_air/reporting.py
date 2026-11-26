import json
from pathlib import Path

import yaml


def _format(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def generate_report(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    with (output_dir / "resolved_config.yaml").open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    dataset = json.loads((output_dir / "dataset_summary.json").read_text(encoding="utf-8"))
    cleaning = json.loads((output_dir / "cleaning_log.json").read_text(encoding="utf-8"))
    source = metrics["data_source"]
    lines = ["# 长春 PM2.5 短期事件预警实验报告", ""]
    if source == "synthetic":
        lines += ["> **以下结果仅验证软件流程，不是长春真实空气质量研究结论。输入为固定随机种子的合成数据。**", ""]
    else:
        lines += ["> 本报告为历史数据研究实验，不可直接作为现实公共预警系统使用。", ""]
    lines += [
        "## 1. 数据与任务", "",
        f"- 数据来源标记：`{source}`。",
        f"- 小时数据覆盖：{cleaning['start']} 至 {cleaning['end']}，对齐后 {cleaning['rows_after_alignment']} 行。",
        f"- 重复时间记录聚合：{cleaning['duplicate_rows_aggregated']}；插值策略：{cleaning['interpolation']}。",
        f"- 输入过去 **{config['lookback']} 小时**，预测未来 **{config['horizon']} 小时**内 PM2.5 是否达到 **{config['pm25_threshold']} μg/m³**。",
        "- 该阈值是预先固定的研究事件定义，不等同于官方小时级公共预警标准。", "",
        "## 2. 时间外划分", "",
        "| 分区 | 样本数 | 正例 | 负例 | 起始 | 结束 |", "|---|---:|---:|---:|---|---|",
    ]
    for name, values in dataset["partitions"].items():
        lines.append(f"| {name} | {values['samples']} | {values['positive']} | {values['negative']} | {values['start']} | {values['end']} |")
    lines += [
        "", "相邻分区起点已清除可能跨分区的窗口；标准化仅用训练集拟合，决策阈值仅由验证集 F1 选择。", "",
        "## 3. 模型对照", "",
        "| 模型 | PR-AUC | Precision | Recall | F1 | FAR | 阈值 | 参数量 | 训练秒 | 推理秒 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in metrics["models"].items():
        test = values["test"]
        lines.append(
            f"| {name} | {_format(test['pr_auc'])} | {_format(test['precision'])} | {_format(test['recall'])} | "
            f"{_format(test['f1'])} | {_format(test['false_alarm_rate'])} | {_format(test['threshold'])} | "
            f"{values['parameters']} | {_format(values['training_seconds'])} | {_format(values['inference_seconds'])} |"
        )
    importances = metrics["models"]["xgboost"]["feature_importances"]
    lines += ["", "XGBoost 主要特征重要性：" + "、".join(f"{name}={_format(rate)}" for name, rate in list(importances.items())[:6]) + "。", ""]
    lines += ["## 4. 图表", ""]
    titles = ["数据质量", "季节与采暖期", "典型污染过程", "污染物与气象滞后关联", "模型 PR 曲线", "模型指标", "XGBoost 成功/漏报/误报案例", "XGBoost 特征重要性与运行开销"]
    for index, title in enumerate(titles, 1):
        matches = sorted((output_dir / "figures").glob(f"{index:02d}_*.png"))
        if matches:
            lines += [f"### {title}", "", f"![{title}](figures/{matches[0].name})", ""]
    lines += [
        "## 5. 结论解释边界", "",
        "- 应优先比较 PR-AUC、召回率和误报率，不能仅凭准确率判断预警价值。",
        "- 简单模型更好时，应如实接受；本流程不预设 XGBoost 必须优于基线。",
        "- 样本外关联与特征重要性不等于污染形成机制或因果效应。",
        "- 气象再分析网格与监测站局地天气并不等价，历史关系也可能随年份变化。",
        "- 运行时间和树数量是软件实验观测，不代表跨硬件的统一计算成本。",
        "- 不同提前量、污染阈值和树数量应使用另行固定的配置做敏感性分析，不能事后只报告最优定义。", "",
        f"随机种子：`{config['seed']}`。完整配置见 `resolved_config.yaml`，预测明细见 `predictions.csv`。", "",
    ]
    report = output_dir / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    return report
