# -*- coding: utf-8 -*-
"""Build the presentation PPT (5-6 min talk) for the Changchun air-quality study."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Cm, Emu, Pt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "artifacts" / "report_figures"
OUT_DIR = ROOT / "artifacts" / "submission"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "55251330_王成烨_汇报PPT.pptx"

# ---------- extra chart: model PR-AUC comparison ----------
metrics = pd.read_csv(ROOT / "artifacts/web-runs/94469c656403/metrics.csv")
test = metrics[metrics["partition"] == "test"].set_index("model")
order = ["persistence", "logistic_regression", "lstm", "xgboost"]
names = ["持续性基线", "逻辑回归", "LSTM", "XGBoost"]
colors = ["#9ca3af", "#5587c9", "#7c93ad", "#0e7c5b"]
fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=160)
vals = [test.loc[m, "pr_auc"] for m in order]
bars = ax.bar(names, vals, color=colors, width=0.55)
for b, v in zip(bars, vals):
    ax.annotate(f"{v:.3f}", (b.get_x() + b.get_width() / 2, v), xytext=(0, 4),
                textcoords="offset points", ha="center", fontsize=11, fontweight="bold")
ax.set_ylabel("测试集 PR-AUC")
ax.set_ylim(0, 0.75)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
pr_fig = FIG / "fig5_1_pr_auc.png"
fig.savefig(pr_fig)
plt.close(fig)

# ---------- theme ----------
DARK = RGBColor(0x0B, 0x3B, 0x36)
ACCENT = RGBColor(0x0E, 0x7C, 0x5B)
GOLD = RGBColor(0xD9, 0x8A, 0x2B)
INK = RGBColor(0x1F, 0x29, 0x33)
GRAY = RGBColor(0x5B, 0x66, 0x70)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG = RGBColor(0xF6, 0xF7, 0xF5)

prs = Presentation()
prs.slide_width = Cm(33.867)
prs.slide_height = Cm(19.05)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height

FONT = "微软雅黑"

def add_rect(slide, x, y, w, h, color, line=False):
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    if not line:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = color
    sh.shadow.inherit = False
    return sh

def add_text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             space_after=6, line_spacing=1.12):
    """runs: list of paragraphs; each paragraph is list of (text, size, bold, color)."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        for text, size, bold, color in para:
            r = p.add_run()
            r.text = text
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
    return tb

def content_slide(title, eyebrow):
    slide = prs.slides.add_slide(BLANK)
    add_rect(slide, 0, 0, SW, SH, BG)
    add_rect(slide, 0, 0, Cm(0.55), SH, ACCENT)
    add_text(slide, Cm(1.2), Cm(0.55), Cm(28), Cm(0.9),
             [[(eyebrow, 12, True, GOLD)]])
    add_text(slide, Cm(1.2), Cm(1.05), Cm(30), Cm(1.4),
             [[(title, 27, True, DARK)]])
    add_rect(slide, Cm(1.25), Cm(2.35), Cm(4.2), Pt(2.6), ACCENT)
    return slide

def bullets(slide, items, x=Cm(1.35), y=Cm(3.0), w=Cm(15.2), size=13.5, gap=8):
    paras = []
    for head, body in items:
        runs = [("▪ ", size, True, ACCENT), (head, size, True, INK)]
        if body:
            runs.append(("　" + body, size, False, GRAY))
        paras.append(runs)
    add_text(slide, x, y, w, Cm(12), paras, space_after=gap)

def add_pic(slide, path, x, y, w=None, h=None):
    return slide.shapes.add_picture(str(path), x, y, width=w, height=h)

def footer(slide, idx, total):
    add_text(slide, SW - Cm(3.2), SH - Cm(0.95), Cm(2.6), Cm(0.6),
             [[(f"{idx:02d} / {total:02d}", 10, False, GRAY)]], align=PP_ALIGN.RIGHT)
    add_text(slide, Cm(1.25), SH - Cm(0.95), Cm(12), Cm(0.6),
             [[("55251330 王成烨 · 数据分析结课报告", 10, False, GRAY)]])

TOTAL = 11

# ================= 1 封面 =================
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, SW, SH, DARK)
add_rect(s, 0, SH - Cm(0.35), SW, Cm(0.35), GOLD)
add_text(s, Cm(2.4), Cm(3.1), Cm(20), Cm(1),
         [[("数据分析结课报告", 16, True, GOLD)]])
add_text(s, Cm(2.4), Cm(4.3), Cm(29), Cm(4.6),
         [[("长春市空气质量时序数据分析", 40, True, WHITE)],
          [("与污染预警研究", 40, True, WHITE)]], line_spacing=1.15)
add_text(s, Cm(2.4), Cm(10.2), Cm(28), Cm(3.2),
         [[("26,304 条小时级观测 · 采暖季污染规律 · 多模型预警对照 · Web 可视化平台", 15, False, RGBColor(0xBF, 0xD8, 0xD2))]])
add_text(s, Cm(2.4), Cm(14.6), Cm(20), Cm(2.6),
         [[("汇报人：王成烨", 16, False, WHITE)],
          [("学号：55251330", 16, False, WHITE)]], space_after=4)
footer_text = add_text(s, SW - Cm(8.4), SH - Cm(1.6), Cm(7.6), Cm(0.8),
                       [[("Open-Meteo CAMS + ERA5", 11, False, RGBColor(0x8F, 0xB5, 0xAE))]], align=PP_ALIGN.RIGHT)

# ================= 2 研究问题 =================
s = content_slide("研究问题与任务定义", "PROBLEM & TASK")
bullets(s, [
    ("研究动机", "长春冬季采暖期污染过程集中，若能提前数小时预警，对出行与健康管理有直接价值。"),
    ("核心问题", "融合历史空气质量与气象序列，能否对污染升高提供有效的短期预警？"),
    ("任务定义", "用过去 48 小时序列，预测未来 6 小时内 PM2.5 是否超过 75 μg/m³（预先定义，不事后调优）。"),
    ("分析主线", "数据质量 → 分布与季节规律 → 气象滞后关联 → 预警建模与模型对照。"),
], y=Cm(3.2), w=Cm(30), size=15, gap=16)
add_rect(s, Cm(1.35), Cm(12.6), Cm(29.9), Cm(3.6), RGBColor(0xE7, 0xEF, 0xEC))
add_text(s, Cm(2.1), Cm(13.0), Cm(28.4), Cm(2.8),
         [[("四个研究问题：", 14, True, DARK)],
          [("RQ1 污染的时间规律　RQ2 污染前的气象与前兆特征　RQ3 能否提前预测　RQ4 各模型的收益与代价", 13.5, False, INK)]],
         space_after=6)
footer(s, 2, TOTAL)

# ================= 3 数据与质量 =================
s = content_slide("数据来源与数据质量", "DATA & QUALITY")
bullets(s, [
    ("获取方式", "自编写 Python 采集程序（Requests），调用 Open-Meteo 空气质量（CAMS）与历史气象（ERA5）接口。"),
    ("数据规模", "2023-11-18 至 2026-11-17，小时粒度，对齐后 26,304 条样本 × 12 个特征字段。"),
    ("字段构成", "6 项污染物（PM2.5、PM10、SO2、NO2、CO、O3）+ 6 项气象（温度、湿度、风速、风向、气压、降水）。"),
    ("质量结论", "缺失率 0%、无重复时间戳、无时间缺口、取值均在合理物理范围，无需插值。"),
    ("预处理", "时区统一 Asia/Shanghai 按小时内连接对齐；CO 单位换算；构造滞后、滚动、周期编码特征，杜绝未来信息泄漏。"),
], y=Cm(3.1), w=Cm(30.5), size=14.5, gap=13)
footer(s, 3, TOTAL)

# ================= 4 分布特征 =================
s = content_slide("单变量分析：右偏分布，重污染稀少", "UNIVARIATE ANALYSIS")
add_pic(s, FIG / "fig3_1_pm25_hist.png", Cm(1.3), Cm(3.1), w=Cm(16.6))
bullets(s, [
    ("右偏分布", "均值 23.0、中位数 18.5 μg/m³，峰值集中于 10–30 区间。"),
    ("重污染稀少", "超过 75 μg/m³ 的小时仅占 1.67%，最大 175.6。"),
    ("建模启示", "类别高度不平衡，评估须用 PR-AUC、召回率而非准确率。"),
], x=Cm(18.6), y=Cm(3.4), w=Cm(14.2), size=13.5, gap=12)
footer(s, 4, TOTAL)

# ================= 5 季节规律 =================
s = content_slide("季节规律：采暖季污染显著偏高", "SEASONALITY")
add_pic(s, FIG / "fig3_2_heating_box.png", Cm(1.3), Cm(3.1), w=Cm(14.6))
add_pic(s, FIG / "fig3_3_monthly.png", Cm(16.6), Cm(3.1), w=Cm(16.2))
add_text(s, Cm(1.5), Cm(12.0), Cm(31), Cm(4.2),
         [[("采暖季（10月–次年4月）均值 25.8 μg/m³，较非采暖季（18.9）偏高约 36%；", 15, True, INK)],
          [("月均浓度呈“冬高夏低”单峰形态：3 月最高 31.7，9 月最低 14.2，与长春采暖周期高度吻合。", 15, False, INK)]],
         space_after=8)
footer(s, 5, TOTAL)

# ================= 6 相关与滞后 =================
s = content_slide("多变量分析：结构性关联与滞后效应", "CORRELATION & LAG")
add_pic(s, FIG / "fig3_4_heatmap.png", Cm(1.3), Cm(3.0), h=Cm(11.4))
bullets(s, [
    ("污染物同源", "PM2.5–PM10 相关 0.92；与 SO2、CO 中等相关（0.58）。"),
    ("光化学特征", "NO2 与 O3 强负相关（-0.63）。"),
    ("扩散条件", "风速、温度与 PM2.5 弱负相关；湿度弱正相关。"),
    ("滞后效应", "温度的负相关随滞后增强，48h 时达 -0.187，为短期预警提供依据。"),
], x=Cm(17.6), y=Cm(3.4), w=Cm(15.2), size=13.5, gap=12)
add_text(s, Cm(1.5), Cm(14.9), Cm(31), Cm(1.6),
         [[("注：相关性仅描述统计关联，不代表因果关系。", 12.5, False, GRAY)]])
footer(s, 6, TOTAL)

# ================= 7 预警任务与模型 =================
s = content_slide("预警任务设计与模型对照", "TASK & MODELS")
add_rect(s, Cm(1.35), Cm(3.1), Cm(30), Cm(3.5), RGBColor(0xE7, 0xEF, 0xEC))
add_text(s, Cm(2.1), Cm(3.45), Cm(28.6), Cm(2.8),
         [[("样本构造", 14, True, DARK)],
          [("输入：过去 48 小时污染 + 气象序列　→　输出：未来 6 小时是否发生 PM2.5 ≥ 75 μg/m³ 事件", 14.5, True, ACCENT)],
          [("时间顺序划分训练/验证/测试（60/20/20），边界清除跨区窗口，阈值仅由验证集确定。", 12.5, False, GRAY)]],
         space_after=5)
bullets(s, [
    ("持续性基线", "以当前污染状态直接作为未来预测，检验模型的真实增量。"),
    ("逻辑回归", "使用滞后、滚动统计等人工特征的线性模型。"),
    ("LSTM", "常见深度时序模型，输入标准化序列。"),
    ("XGBoost", "梯度提升树（140 棵、深度 4），与逻辑回归共享表格特征。"),
], y=Cm(7.3), w=Cm(30.4), size=14, gap=10)
footer(s, 7, TOTAL)

# ================= 8 结果对比 =================
s = content_slide("时间外测试结果：XGBoost 最优", "RESULTS")
add_pic(s, pr_fig, Cm(1.3), Cm(3.1), w=Cm(16.8))
bullets(s, [
    ("XGBoost", "PR-AUC 0.610、F1 0.611、召回率 0.539、误报率仅 0.5%。"),
    ("逻辑回归", "PR-AUC 0.589，简单模型是有竞争力的参照。"),
    ("LSTM", "PR-AUC 0.501，深度序列模型未占优。"),
    ("持续性基线", "PR-AUC 0.350，明显落后于学习类模型。"),
    ("结论", "学习类模型相对基线有真实增益；梯度提升树在本任务性价比最高。"),
], x=Cm(18.6), y=Cm(3.4), w=Cm(14.3), size=13.5, gap=11)
footer(s, 8, TOTAL)

# ================= 9 可视化平台 =================
s = content_slide("AeriScope Web 可视化研究驾驶舱", "VISUALIZATION")
add_pic(s, FIG / "fig4_1_web_data.png", Cm(1.3), Cm(3.1), w=Cm(15.6))
add_pic(s, FIG / "fig4_2_web_models.png", Cm(17.3), Cm(3.1), w=Cm(15.6))
add_text(s, Cm(1.5), Cm(12.4), Cm(31), Cm(4.4),
         [[("React + FastAPI 前后端分离，数据处理与模型计算全部留在 Python，结果可复现；", 14.5, True, INK)],
          [("七个交互视图：研究总览、数据洞察、模型对照、XGBoost 实验室、情景推演、误差案例、运行实验；", 13.5, False, INK)],
          [("时间刷联动探索污染与气象序列，拖动阈值实时查看混淆矩阵与误报/漏报取舍。", 13.5, False, INK)]],
         space_after=8)
footer(s, 9, TOTAL)

# ================= 10 结论 =================
s = content_slide("结论与局限", "CONCLUSION")
bullets(s, [
    ("数据规律", "长春 PM2.5 呈右偏分布、采暖季显著偏高（+36%），与气象条件存在可持续至 48 小时的滞后关联。"),
    ("预警可行", "XGBoost 在时间外测试取得 PR-AUC 0.610、召回率 0.539、误报率 0.5%，显著优于持续性基线。"),
    ("平台产出", "分析报告 + 可复现实验流水线 + AeriScope 交互式可视化平台三位一体。"),
], y=Cm(3.2), w=Cm(30.4), size=14.5, gap=12)
add_rect(s, Cm(1.35), Cm(10.6), Cm(30), Cm(5.6), RGBColor(0xFB, 0xF3, 0xE3))
add_text(s, Cm(2.1), Cm(11.0), Cm(28.6), Cm(4.8),
         [[("局限与边界", 14, True, GOLD)],
          [("① 再分析格点数据与地面站点观测存在系统性差异；② 统计关联不等于污染成因；", 13, False, INK)],
          [("③ 单一阈值定义事件，结论存在阈值敏感性；④ 模型结果不可直接用于现实公共预警。", 13, False, INK)]],
         space_after=6)
footer(s, 10, TOTAL)

# ================= 11 致谢 =================
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, SW, SH, DARK)
add_rect(s, 0, SH - Cm(0.35), SW, Cm(0.35), GOLD)
add_text(s, 0, Cm(7.2), SW, Cm(3), [[("恳请老师批评指正", 40, True, WHITE)]], align=PP_ALIGN.CENTER)
add_text(s, 0, Cm(10.6), SW, Cm(1.4),
         [[("王成烨 · 55251330 · 长春市空气质量时序数据分析与污染预警研究", 15, False, RGBColor(0xBF, 0xD8, 0xD2))]],
         align=PP_ALIGN.CENTER)

prs.save(str(OUT))
print("saved:", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
