# -*- coding: utf-8 -*-
"""Generate Chinese-labeled figures for the course report from real observed data."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "report_figures"
OUT.mkdir(parents=True, exist_ok=True)
RUN = ROOT / "artifacts" / "web-runs" / "94469c656403"

air = pd.read_csv(ROOT / "data/raw/changchun_air_observed.csv", parse_dates=["time"])
wea = pd.read_csv(ROOT / "data/raw/changchun_weather_observed.csv", parse_dates=["time"])
df = air.merge(wea, on="time", how="inner")
df["month"] = df["time"].dt.month
heating_months = {10, 11, 12, 1, 2, 3, 4}
df["is_heating"] = df["month"].isin(heating_months)

BLUE, ORANGE, GRAY = "#2c7fb8", "#e6550d", "#636363"

# 图3-1 PM2.5 直方图 + KDE
fig, ax = plt.subplots(figsize=(7.0, 3.9), dpi=160)
vals = df["pm25"].to_numpy()
ax.hist(vals, bins=80, range=(0, 180), density=True, color=BLUE, alpha=0.75, edgecolor="white", linewidth=0.2)
xs = np.linspace(0, 180, 600)
bw = 1.06 * vals.std() * len(vals) ** (-1 / 5)
kde = np.exp(-0.5 * ((xs[:, None] - vals[None, :]) / bw) ** 2).sum(axis=1) / (len(vals) * bw * np.sqrt(2 * np.pi))
ax.plot(xs, kde, color=ORANGE, lw=1.8, label="核密度估计")
ax.axvline(vals.mean(), color=GRAY, ls="--", lw=1.2, label=f"均值 {vals.mean():.1f}")
ax.axvline(np.median(vals), color="#238b45", ls=":", lw=1.4, label=f"中位数 {np.median(vals):.1f}")
ax.set_xlabel("PM2.5 浓度（μg/m³）")
ax.set_ylabel("频数密度")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "fig3_1_pm25_hist.png")
plt.close(fig)

# 图3-2 采暖季 vs 非采暖季箱线图
fig, ax = plt.subplots(figsize=(6.2, 3.9), dpi=160)
groups = [df.loc[~df["is_heating"], "pm25"], df.loc[df["is_heating"], "pm25"]]
bp = ax.boxplot(groups, tick_labels=["非采暖季（5–9月）", "采暖季（10月–次年4月）"], showfliers=False,
                patch_artist=True, widths=0.45, medianprops=dict(color="black", lw=1.5))
for patch, c in zip(bp["boxes"], [BLUE, ORANGE]):
    patch.set_facecolor(c)
    patch.set_alpha(0.75)
means = [g.mean() for g in groups]
for i, m in enumerate(means, 1):
    ax.scatter(i, m, marker="D", color="white", edgecolor="black", zorder=3, s=28)
    ax.annotate(f"均值 {m:.1f}", (i, m), textcoords="offset points", xytext=(10, 6), fontsize=9)
ax.set_ylabel("PM2.5 浓度（μg/m³）")
fig.tight_layout()
fig.savefig(OUT / "fig3_2_heating_box.png")
plt.close(fig)

# 图3-3 月度均值曲线
fig, ax = plt.subplots(figsize=(7.0, 3.9), dpi=160)
monthly = df.groupby("month")["pm25"].mean()
ax.axvspan(9.5, 12.5, color=ORANGE, alpha=0.08)
ax.axvspan(0.5, 4.5, color=ORANGE, alpha=0.08)
ax.plot(monthly.index, monthly.values, marker="o", color=BLUE, lw=2)
for x, y in monthly.items():
    ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5)
ax.set_xticks(range(1, 13))
ax.set_xlabel("月份")
ax.set_ylabel("PM2.5 月均浓度（μg/m³）")
ax.text(2.5, monthly.max() + 1.5, "采暖季", ha="center", fontsize=9, color=ORANGE)
ax.text(11, monthly.max() + 1.5, "采暖季", ha="center", fontsize=9, color=ORANGE)
ax.set_ylim(0, monthly.max() + 6)
fig.tight_layout()
fig.savefig(OUT / "fig3_3_monthly.png")
plt.close(fig)

# 图3-4 相关性热力图
cols = ["pm25", "pm10", "so2", "no2", "co", "o3", "temperature", "humidity", "wind_speed", "pressure", "precipitation"]
labels = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3", "温度", "湿度", "风速", "气压", "降水"]
corr = df[cols].corr()
fig, ax = plt.subplots(figsize=(7.0, 5.9), dpi=160)
im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(cols)), labels, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(cols)), labels, fontsize=9)
for i in range(len(cols)):
    for j in range(len(cols)):
        v = corr.iloc[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7.5,
                color="white" if abs(v) > 0.55 else "black")
fig.colorbar(im, ax=ax, shrink=0.85, label="皮尔逊相关系数")
fig.tight_layout()
fig.savefig(OUT / "fig3_4_heatmap.png")
plt.close(fig)

# 图3-5 气象变量与 PM2.5 滞后相关
lag = pd.read_csv(RUN / "eda" / "lag_correlations.csv")
name_map = {"temperature": "温度", "humidity": "湿度", "wind_speed": "风速", "pressure": "气压"}
fig, ax = plt.subplots(figsize=(7.0, 3.9), dpi=160)
for var, cn in name_map.items():
    sub = lag[lag["variable"] == var].sort_values("lag_hours")
    ax.plot(sub["lag_hours"], sub["correlation"], marker="o", ms=3.5, lw=1.6, label=cn)
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xlabel("滞后时长（小时）")
ax.set_ylabel("与 PM2.5 的相关系数")
ax.legend(fontsize=9, ncol=4)
fig.tight_layout()
fig.savefig(OUT / "fig3_5_lag.png")
plt.close(fig)

print("figures saved to", OUT)
for p in sorted(OUT.glob("*.png")):
    print(" ", p.name, p.stat().st_size // 1024, "KB")
