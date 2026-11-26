import { Activity, ArrowRight, BrainCircuit, Clock3, Database, ShieldCheck, Target, TriangleAlert } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DashboardData, PageId } from '../types'
import { MetricCard, PageHeader, Panel, formatNumber, modelColors, modelNames } from '../components/ui'

export default function OverviewPage({ data, onNavigate }: { data: DashboardData; onNavigate: (page: PageId) => void }) {
  const xgboost = data.models.find((model) => model.name === 'xgboost')!
  const best = [...data.models].sort((a, b) => (b.test.pr_auc ?? 0) - (a.test.pr_auc ?? 0))[0]
  const test = data.dataset.partitions.test
  const chartModels = data.models.map((model) => ({ ...model, display: modelNames[model.name], value: model.test.pr_auc }))
  return <div className="page-stack">
    <PageHeader eyebrow="RESEARCH OVERVIEW / 01" title="从污染过程，到提前预警。" description="融合历史空气质量与气象序列，以统一时间外测试审视四类模型的真实代价。" action={<button className="button secondary desktop-action" onClick={() => onNavigate('models')}>查看完整对照<ArrowRight size={16} /></button>} />

    <section className="research-hero">
      <div className="hero-copy"><span className="hero-kicker"><span className="status-dot" />CHANGCHUN · WINTER AIR STUDY</span><h2>用过去 <em>{data.config.lookback}</em> 小时<br />洞察未来 <em>{data.config.horizon}</em> 小时</h2><p>预先定义 PM2.5 ≥ {data.config.pm25_threshold} μg/m³ 为研究事件。比较精度、漏报、误报与特征重要性，而非只追求单一分数。</p><div className="hero-tags"><span><Clock3 size={14} />时间外测试</span><span><ShieldCheck size={14} />无泄漏窗口</span><span><BrainCircuit size={14} />梯度提升树</span></div></div>
      <div className="hero-orbit" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><Activity size={31} /><strong>{data.config.xgb_estimators}</strong><span>BOOSTING ROUNDS</span></div><span className="orbit-node node-one" /><span className="orbit-node node-two" /><span className="orbit-node node-three" /></div>
      <div className="hero-foot"><span>{data.cleaning.start.slice(0, 10)} — {data.cleaning.end.slice(0, 10)}</span><span>{data.cleaning.rows_after_alignment.toLocaleString()} 小时记录</span></div>
    </section>

    <div className="metric-grid">
      <MetricCard label="最佳测试 PR-AUC" value={formatNumber(best.test.pr_auc)} detail={`${modelNames[best.name]} · 时间外测试`} icon={<Target size={20} />} />
      <MetricCard label="XGBoost 事件召回率" value={(xgboost.test.recall * 100).toFixed(1)} suffix="%" detail={`漏报 ${xgboost.test.fn} 个预测窗口`} icon={<Activity size={20} />} tone="blue" />
      <MetricCard label="XGBoost 误报率" value={(xgboost.test.false_alarm_rate! * 100).toFixed(1)} suffix="%" detail={`误报 ${xgboost.test.fp} 个预测窗口`} icon={<TriangleAlert size={20} />} tone="coral" />
      <MetricCard label="独立测试样本" value={test.samples.toLocaleString()} detail={`${test.positive.toLocaleString()} 正例 / ${test.negative.toLocaleString()} 负例`} icon={<Database size={20} />} tone="gold" />
    </div>

    <div className="dashboard-grid two-one">
      <Panel eyebrow="MODEL BENCHMARK" title="模型精度对照" action={<button className="text-button" onClick={() => onNavigate('models')}>PR 曲线<ArrowRight size={14} /></button>}>
        <p className="panel-description">PR-AUC 越高越好 · 阈值不影响该指标</p>
        <div className="chart-lg"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartModels} layout="vertical" margin={{ left: 8, right: 24 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--chart-grid)" /><XAxis type="number" domain={[0, 1]} tick={{ fill: 'var(--muted)', fontSize: 11 }} /><YAxis type="category" dataKey="display" width={86} tick={{ fill: 'var(--text)', fontSize: 12 }} axisLine={false} tickLine={false} /><Tooltip formatter={(value) => [formatNumber(Number(value)), 'PR-AUC']} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10 }} /><Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>{chartModels.map((model) => <Cell key={model.name} fill={modelColors[model.name]} />)}</Bar></BarChart></ResponsiveContainer></div>
      </Panel>
      <Panel eyebrow="SEASONAL RHYTHM" title="月度污染节奏"><p className="panel-description">月均 PM2.5 · μg/m³</p><div className="chart-lg"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.monthly} margin={{ top: 16, right: 4, left: -20 }}><defs><linearGradient id="monthlyFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#168573" stopOpacity={0.35} /><stop offset="1" stopColor="#168573" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={{ fill: 'var(--muted)', fontSize: 11 }} /><YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} /><Tooltip formatter={(value) => [Number(value).toFixed(1), 'PM2.5']} labelFormatter={(label) => `${label} 月`} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10 }} /><Area type="monotone" dataKey="mean" stroke="#168573" strokeWidth={2.5} fill="url(#monthlyFill)" /></AreaChart></ResponsiveContainer></div></Panel>
    </div>

    <div className="dashboard-grid two-one bottom-grid deferred">
      <Panel eyebrow="RESEARCH INTERPRETATION" title="结果如何解读"><div className="finding-list"><article><span className="finding-index">01</span><div><h3>简单模型是有价值的参照</h3><p>本次演示中 {modelNames[best.name]} 的 PR-AUC 最高。XGBoost 并未被预设为必然优于传统方法。</p></div></article><article><span className="finding-index">02</span><div><h3>召回率需要与误报一起阅读</h3><p>XGBoost 找到 {(xgboost.test.recall * 100).toFixed(1)}% 的事件窗口，同时产生 {(xgboost.test.false_alarm_rate! * 100).toFixed(1)}% 的负例误报。</p></div></article><article><span className="finding-index">03</span><div><h3>特征重要性不等于因果效应</h3><p>当前展示树模型的分裂重要性、树数量与运行时间，不把关联解释为污染形成机制。</p></div></article></div></Panel>
      <Panel eyebrow="STUDY PROTOCOL" title="实验协议"><dl className="protocol-list"><div><dt>数据对齐</dt><dd>小时级 · Asia/Shanghai</dd></div><div><dt>插值策略</dt><dd>{data.cleaning.interpolation === 'none' ? '不插值，保留真实缺口' : data.cleaning.interpolation}</dd></div><div><dt>测试起点</dt><dd>{test.start.slice(0, 10)}</dd></div><div><dt>测试终点</dt><dd>{test.end.slice(0, 10)}</dd></div><div><dt>随机种子</dt><dd>{data.config.seed}</dd></div></dl><div className="research-warning"><ShieldCheck size={18} /><p>{data.data_source === 'synthetic' ? '当前为合成数据，仅验证研究软件流程。' : '历史研究结果不可直接用于公共预警。'}</p></div></Panel>
    </div>
  </div>
}
