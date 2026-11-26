# -*- coding: utf-8 -*-
"""Build the course report docx from the provided template (55251330 王成烨)."""
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(
    "C:/Users/王成烨/.kimi-code/sessions/wd_test2_314ae28f0839/"
    "session_8d571c17-d17d-4807-8477-455bc952180c/attachments/"
    "f_a52c61b1-45f0-4c81-b12a-e459e012111a-结课报告题目【模版】_数据分析.docx"
)
FIG = ROOT / "artifacts" / "report_figures"
OUT_DIR = ROOT / "artifacts" / "submission"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "55251330_王成烨_长春市空气质量时序数据分析与污染预警研究.docx"

TITLE = "长春市空气质量时序数据分析与污染预警研究"

doc = Document(str(TEMPLATE))

# table style used by the template's example table (read before clearing body)
TABLE_STYLE = "Table Grid"
for t in doc.tables:
    if t.style is not None:
        TABLE_STYLE = t.style.name
    break

# ---------- keep title & student-info paragraphs, drop everything else ----------
body = doc.element.body
children = list(body)
kept = 0
for el in children:
    tag = el.tag.rsplit("}", 1)[-1]
    if tag == "p" and kept < 2:
        kept += 1
        continue
    if tag == "sectPr":
        continue
    body.remove(el)

paras = doc.paragraphs
title_p, info_p = paras[0], paras[1]

def rewrite(paragraph, text):
    runs = paragraph.runs
    runs[0].text = text
    for r in runs[1:]:
        r._element.getparent().remove(r._element)

rewrite(title_p, TITLE)
rewrite(info_p, "55251330  王成烨")

# ---------- style helpers ----------
def set_font(run, east="宋体", ascii_="Times New Roman", size=12, bold=False):
    run.font.name = ascii_
    run.font.size = Pt(size)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), east)

def add_body(text, indent=True):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    if indent:
        p.paragraph_format.first_line_indent = Pt(24)
    r = p.add_run(text)
    set_font(r)
    return p

def add_h2(text):
    p = doc.add_paragraph(text, style="Heading 2")
    return p

def add_h3(text):
    p = doc.add_paragraph(text, style="Heading 3")
    return p

def add_caption(text):
    try:
        p = doc.add_paragraph(style="图注")
    except KeyError:
        p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_font(r, east="黑体", size=10.5)
    return p

def add_figure(filename, caption, width=Cm(14)):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(FIG / filename), width=width)
    add_caption(caption)

def add_table(header, rows, caption):
    add_caption(caption)
    table = doc.add_table(rows=len(rows) + 1, cols=len(header))
    table.style = TABLE_STYLE
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(header):
        cell = table.rows[0].cells[j]
        cell.text = ""
        r = cell.paragraphs[0].add_run(h)
        set_font(r, size=10.5, bold=True)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = ""
            r = cell.paragraphs[0].add_run(str(v))
            set_font(r, size=10.5)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

# ---------- descriptive stats for 表3-1 ----------
air = pd.read_csv(ROOT / "data/raw/changchun_air_observed.csv", parse_dates=["time"])
wea = pd.read_csv(ROOT / "data/raw/changchun_weather_observed.csv", parse_dates=["time"])
df = air.merge(wea, on="time", how="inner")
N = len(df)

def stat(col):
    s = df[col]
    return [f"{N}", f"{s.mean():.2f}", f"{s.median():.2f}", f"{s.std():.2f}", f"{s.max():.2f}"]

# ================= 一、数据集来源 =================
add_h2("一、数据集来源")
add_body(
    "本文所采用实验数据集为长春市空气质量与气象小时级观测数据集。数据通过自行编写的数据采集程序，"
    "从 Open-Meteo 开放数据平台下载获取，存储格式为 CSV 格式。数据集时间范围为 2023 年 11 月 18 日至 "
    "2026 年 11 月 17 日，时间粒度为 1 小时，对齐后共计包含 26,304 条样本，特征维度为 12 维（不含时间戳），"
    "数据集主要特征字段信息如表1-1所示。"
)
add_table(
    ["字段名称", "字段含义", "单位", "数据类型"],
    [
        ["time", "观测时间戳（北京时间，小时粒度）", "—", "时间类型"],
        ["pm25", "PM2.5 浓度", "μg/m³", "数值型"],
        ["pm10", "PM10 浓度", "μg/m³", "数值型"],
        ["so2", "二氧化硫（SO2）浓度", "μg/m³", "数值型"],
        ["no2", "二氧化氮（NO2）浓度", "μg/m³", "数值型"],
        ["co", "一氧化碳（CO）浓度", "mg/m³", "数值型"],
        ["o3", "臭氧（O3）浓度", "μg/m³", "数值型"],
        ["temperature", "2 米气温", "℃", "数值型"],
        ["humidity", "2 米相对湿度", "%", "数值型"],
        ["wind_speed", "10 米风速", "km/h", "数值型"],
        ["wind_direction", "10 米风向", "°", "数值型"],
        ["pressure", "地面气压", "hPa", "数值型"],
        ["precipitation", "小时降水量", "mm", "数值型"],
    ],
    "表1-1 数据集主要特征字段信息",
)
add_h3("1.1 爬虫概述")
add_body(
    "本文数据通过自行编写的数据采集程序获取。程序使用 Python 的 Requests 库，分别调用 Open-Meteo 平台的"
    "空气质量接口（air-quality-api.open-meteo.com，CAMS 大气成分再分析数据）与历史气象接口"
    "（archive-api.open-meteo.com，ERA5 再分析数据），采集长春市区（北纬 43.88°、东经 125.35°）"
    "2023 年 11 月 18 日至 2026 年 11 月 17 日的小时级数据，共获取 26,304 条有效数据。程序按年度分块发起"
    "请求并内置失败重试机制，数据经解析、字段重命名与单位换算后存储为 CSV 格式，空气质量数据包含 PM2.5、"
    "PM10、SO2、NO2、CO、O3 共 6 个特征字段，气象数据包含温度、相对湿度、风速、风向、气压、降水共 6 个特征字段。"
    "Open-Meteo 为免费开放接口，无反爬限制，采集过程未触发访问控制。"
)

# ================= 二、数据预处理 =================
add_h2("二、数据预处理")
add_h3("2.1 数据清洗")
add_body(
    "（1）缺失值处理：对全部字段进行缺失率统计，12 个字段缺失率均为 0%，本数据无缺失问题，未执行插值或删除操作。"
)
add_body(
    "（2）重复值处理：按时间戳检查重复记录，26,304 条样本中无重复时间戳，本数据无此问题。"
)
add_body(
    "（3）异常值处理：对各字段进行物理取值范围核查与分布检查，PM2.5 最大值为 175.6 μg/m³、气温范围为 "
    "-28.9 ℃ 至 36.3 ℃，各字段取值均处于合理观测范围内，未发现异常值，未做剔除或截断处理。"
)
add_body(
    "（4）时间对齐：相邻记录时间间隔均为 1 小时，无时间缺口；空气质量数据与气象数据统一为 Asia/Shanghai "
    "时区的小时级时间戳，按时间戳内连接精确对齐，对齐后保留 26,304 条样本，并记录清洗日志。"
)
add_h3("2.2 数据转换")
add_body(
    "（1）格式转换：将时间字段由文本解析为日期时间类型，便于排序、对齐与周期特征提取；CO 浓度单位由接口返回的 "
    "μg/m³ 换算为常用的 mg/m³。"
)
add_body(
    "（2）特征构造：由时间戳提取月份、小时、星期，并构造是否为采暖季（10 月至次年 4 月）标志；为防止周期编码"
    "不连续，对小时、星期、月份及风向进行正弦/余弦变换；为刻画污染积累过程，构造 PM2.5 的滞后特征（滞后 1、3、"
    "6、12、24 小时）、滚动统计特征（6 小时与 24 小时滚动均值、滚动最大值）与变化率特征（1、6、24 小时变化量）。"
    "所有滚动与滞后特征仅使用当前时刻及之前的数据，避免引入未来信息。"
)
add_body(
    "（3）数值标准化：建模前对数值特征做标准化处理，标准化参数仅在训练集上估计，再应用于验证集与测试集。"
    "原始分析字段均为数值类型，无需额外编码转换。"
)
add_h3("2.3 数据筛选")
add_body(
    "本分析以 PM2.5 为核心研究对象，保留 6 项污染物字段与 6 项气象字段共 12 个有效字段。剔除的字段包括："
    "时间戳仅用于对齐与排序，不作为分析或建模的输入特征；风向原始角度值在相关性分析中不直接使用，建模时以"
    "正弦/余弦编码替代；数据接口返回的其余指标（如云量、能见度等）与本文研究目标无关，下载阶段即未纳入数据集。"
)

# ================= 三、探索性数据分析 =================
add_h2("三、探索性数据分析")
add_h3("3.1 单变量分析")
add_body(
    f"绘制 PM2.5 浓度的频数分布直方图，并叠加核密度估计曲线，如图3-1所示。结果显示，PM2.5 呈明显右偏分布："
    f"均值为 {df['pm25'].mean():.1f} μg/m³，中位数为 {df['pm25'].median():.1f} μg/m³，大部分时段空气质量较好；"
    "峰值集中在 10～30 μg/m³ 区间，高浓度样本稀疏，最大值为 175.6 μg/m³，超过 75 μg/m³ 的污染小时仅占 1.67%，"
    "呈现典型的“常态清洁、少数重污染”特征。"
)
add_figure("fig3_1_pm25_hist.png", "图3-1 PM2.5 浓度分布直方图")
add_body(
    "对主要污染物与气象字段进行描述性统计分析，统计结果如表3-1所示。从均值与中位数来看，PM2.5、PM10、SO2 等"
    "污染物字段均呈现右偏分布（均值明显大于中位数），O3、温度、湿度、气压等字段分布相对对称。"
)
add_table(
    ["字段", "样本数", "均值", "中位数", "标准差", "最大值"],
    [
        ["PM2.5（μg/m³）"] + stat("pm25"),
        ["PM10（μg/m³）"] + stat("pm10"),
        ["SO2（μg/m³）"] + stat("so2"),
        ["NO2（μg/m³）"] + stat("no2"),
        ["CO（mg/m³）"] + stat("co"),
        ["O3（μg/m³）"] + stat("o3"),
        ["温度（℃）"] + stat("temperature"),
        ["湿度（%）"] + stat("humidity"),
        ["风速（km/h）"] + stat("wind_speed"),
        ["气压（hPa）"] + stat("pressure"),
        ["降水（mm）"] + stat("precipitation"),
    ],
    "表3-1 主要数值字段描述性统计",
)
add_body(
    "进一步按采暖季（10 月至次年 4 月）与非采暖季（5 月至 9 月）分组绘制 PM2.5 箱线图，如图3-2所示。"
    "采暖季 PM2.5 均值为 25.8 μg/m³、中位数为 20.7 μg/m³，明显高于非采暖季的 18.9 μg/m³ 与 16.1 μg/m³，"
    "且采暖季的上四分位数与极端高值更多，表明采暖季污染水平整体抬升、重污染过程集中出现。"
)
add_figure("fig3_2_heating_box.png", "图3-2 采暖季与非采暖季 PM2.5 箱线图对比")
add_body(
    "绘制 PM2.5 月均浓度变化曲线，如图3-3所示。PM2.5 呈现明显的季节节律：11 月至次年 4 月维持高位"
    "（3 月均值最高，为 31.7 μg/m³，与采暖末期及春季沙尘影响有关），5 月起快速回落，9 月最低（14.2 μg/m³），"
    "10 月后再度攀升，与长春市采暖周期高度吻合。"
)
add_figure("fig3_3_monthly.png", "图3-3 PM2.5 月均浓度变化曲线")
add_h3("3.2 多变量相关性分析")
add_body(
    "计算 11 个数值字段之间的皮尔逊相关系数并绘制热力图，如图3-4所示。主要规律包括：PM2.5 与 PM10 的相关系数"
    "高达 0.92，二者同源性强；PM2.5 与 SO2（0.58）、CO（0.58）、NO2（0.46）呈中等正相关，反映燃烧源排放的"
    "共同影响；NO2 与 O3 呈强负相关（-0.63），符合光化学滴定效应；气象变量中，温度与气压呈强负相关（-0.71），"
    "PM2.5 与风速（-0.13）、温度（-0.11）呈弱负相关，与湿度呈弱正相关（0.15），说明静稳、低风速天气不利于"
    "污染物扩散。需要强调的是，相关性仅描述统计关联，不代表因果关系。"
)
add_figure("fig3_4_heatmap.png", "图3-4 污染物与气象变量相关性热力图")
add_body(
    "进一步考察气象变量与 PM2.5 的滞后相关关系，如图3-5所示。温度与 PM2.5 的负相关随滞后时长增加而增强，"
    "滞后 48 小时时相关系数达 -0.187；湿度与 PM2.5 的相关由同期弱正相关（0.150）转为滞后 34 小时的负相关"
    "（-0.181）；风速在各滞后时长下均保持弱负相关（同期 -0.129）；气压则随滞后增加转为弱正相关"
    "（滞后 23 小时达 0.167）。上述结果表明，气象条件对污染水平的影响具有持续数小时至两天的滞后效应，"
    "为利用历史气象序列开展污染短期预警提供了统计依据。"
)
add_figure("fig3_5_lag.png", "图3-5 气象变量与 PM2.5 滞后相关系数")
add_h3("3.3 数据特征总结")
add_body("结合上述可视化图表，可总结以下核心特征：")
add_body("（1）污染水平整体右偏，重污染事件稀少：PM2.5 均值 23.0 μg/m³、中位数 18.5 μg/m³，超过 75 μg/m³ "
         "的污染小时仅占 1.67%，数据存在显著的类别不平衡，分析与建模均需关注少数高污染样本。")
add_body("（2）季节规律显著且与采暖周期吻合：采暖季 PM2.5 均值（25.8 μg/m³）较非采暖季（18.9 μg/m³）偏高约 "
         "36%，月均浓度呈“冬高夏低”的单峰形态，冬季是污染预警的重点时段。")
add_body("（3）污染物之间、污染与气象之间存在结构性关联：PM2.5 与 PM10 强相关，与 SO2、CO 中等相关；风速、"
         "温度与 PM2.5 呈弱负相关，且影响可持续至滞后 48 小时，表明历史气象序列对短期污染预警具有利用价值。")

# ================= 四、可视化展示 =================
add_h2("四、可视化展示")
add_h3("4.1 可视化展示方案设计")
add_body(
    "为直观呈现数据规律与分析结果，设计并实现了“AeriScope 澄空”Web 可视化研究驾驶舱。系统采用前后端分离架构："
    "前端使用 React + TypeScript 构建交互式页面，后端使用 FastAPI 提供数据接口，数据清洗、统计计算与模型评估"
    "全部保留在 Python 侧完成，保证结果可复现。页面划分为研究总览、数据洞察、模型对照、XGBoost 实验室、"
    "情景推演、误差案例、运行实验共七个功能视图，支持明暗双主题与快捷时间范围筛选。展示目的是将本报告第三章的"
    "静态分析结论转化为可交互探索的动态视图，并在此基础上展示基于数据分析结果构建的 PM2.5 短期污染预警模型效果。"
)
add_h3("4.2 可视化展示实现与效果")
add_body(
    "数据洞察视图如图4-1所示。页面上方以统计卡片展示有效小时序列、事件预测窗口（853 个）、原始污染过程（85 次）"
    "与最长过程（22 小时）等核心指标；中部“PM2.5 与气象同步探索”模块绘制全部小时级序列，支持拖动时间刷与"
    "快捷区间（全部、近一年、近 90 天）联动缩放，污染曲线与气象曲线同步变化；右侧“采暖期对照”模块直接对比"
    "采暖季（25.8 μg/m³）与非采暖季（18.9 μg/m³）的平均污染水平，与图3-2的静态分析结论一致。"
)
add_figure("fig4_1_web_data.png", "图4-1 数据洞察视图（真实观测数据）", width=Cm(15))
add_body(
    "模型对照视图如图4-2所示。页面顶部以卡片形式对比持续性基线、逻辑回归、LSTM 与 XGBoost 四类模型在独立测试集"
    "上的 PR-AUC；中部“阈值实验室”允许用户拖动决策阈值，实时刷新 Precision、Recall、F1、误报率与混淆矩阵，"
    "直观展示预警模型在“宁可误报”与“宁可漏报”之间的取舍。用户可通过左侧导航在七个视图间切换，所有图表均"
    "基于真实观测数据的固定实验结果渲染。"
)
add_figure("fig4_2_web_models.png", "图4-2 模型对照与阈值实验室视图", width=Cm(15))
add_h3("4.3 可视化展示总结")
add_body("（1）实现了完整的数据可视化 Web 平台，覆盖数据质量、季节规律、滞后关联与模型评估七个视图，"
         "将报告中的静态结论全部转化为可交互验证的动态图表，达到辅助讲解与复核分析结果的效果。")
add_body("（2）采用前后端分离与“计算全部留在 Python”的设计，页面展示结果与实验产物严格一致，支持按固定"
         "配置重现实验并即时刷新页面，保证了分析结论的可复现性。")
add_body("（3）可改进方向：当前系统运行于本地，后续可部署至公网便于访问；可增加多城市对比视图与更多气象因子"
         "（如边界层高度）的联动分析，进一步丰富展示维度。")

# ================= 五、总结与展望 =================
add_h2("五、总结与展望")
add_h3("5.1 总结")
add_body(
    "本次实验围绕长春市空气质量数据完成了完整的数据分析流程：编写数据采集程序获取 2023 年 11 月至 2026 年 "
    "11 月共 26,304 条小时级空气质量与气象数据；完成缺失、重复、异常与时间对齐等数据质量检查，数据质量良好；"
    "通过直方图、箱线图、月度曲线、相关性热力图与滞后相关分析，系统刻画了长春污染水平“右偏分布、采暖季偏高、"
    "与气象条件存在滞后关联”的核心规律；并开发了 AeriScope Web 可视化平台，将分析结论转化为交互式视图。"
    "在数据分析基础上，进一步构建了 PM2.5 短期污染预警任务（过去 48 小时预测未来 6 小时是否超过 75 μg/m³），"
    "XGBoost 模型在独立测试集上取得 PR-AUC 0.610、F1 0.611、召回率 0.539、误报率 0.5% 的效果，优于持续性基线"
    "（PR-AUC 0.350）与 LSTM（0.501），验证了数据分析结论对预警建模的支撑作用。"
)
add_h3("5.2 展望")
add_body(
    "本研究仍存在不足：数据来源于再分析格点产品，与地面监测站观测存在系统性差异；气象因子仅涵盖常规六项，"
    "未引入边界层高度、风向输送等更贴近污染扩散机制的变量；预警模型仅以单一阈值定义污染事件，结论对阈值选择"
    "较为敏感。后续可延长数据年份、补充多源观测交叉验证，开展阈值与预测提前量的敏感性分析，并尝试序列到序列的"
    "深度模型。需要强调的是，本文揭示的是统计关联而非污染成因，模型结果不能直接用于现实公共预警。"
)

doc.save(str(OUT))
print("saved:", OUT)
