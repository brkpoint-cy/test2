import { useCallback, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useRemoteData } from '../hooks/useRemoteData'
import { ErrorState, LoadingState, PageHeader, Panel, SourceBadge, formatNumber, modelColors, modelNames } from '../components/ui'
import ThresholdLab from '../components/ThresholdLab'
import type { Metrics } from '../types'

type MetricKey = 'pr_auc' | 'f1' | 'recall' | 'false_alarm_rate'
const metricLabels: Record<MetricKey, string> = { pr_auc: 'PR-AUC', f1: 'F1', recall: '召回率', false_alarm_rate: '误报率' }

export default function ModelsPage() {
  const loader = useCallback(api.models, [])
  const { data, error, retry } = useRemoteData(loader, { cacheKey: 'models' })
  const [metric, setMetric] = useState<MetricKey>('pr_auc')
  if (error) return <ErrorState message={error} retry={retry} />
  if (!data) return <LoadingState label="正在汇总模型与 PR 曲线" />
  const bars = data.models.map((model) => ({ name: model.name, display: modelNames[model.name], value: model.test[metric] }))
  return <div className="page-stack">
    <PageHeader eyebrow="MODEL ARENA / 03" title="同一样本，同一把尺。" description="所有模型共享时间划分与测试样本；决策阈值仅由验证集确定。" action={<SourceBadge source={data.data_source} />} />
    <div className="model-summary-strip">{data.models.map((model) => <article key={model.name}><span className="model-color" style={{ background: modelColors[model.name] }} /><div><strong>{modelNames[model.name]}</strong><span>阈值 {formatNumber(model.test.threshold)}</span></div><b>{formatNumber(model.test.pr_auc)}</b><small>PR-AUC</small></article>)}</div>
    <ThresholdLab models={data.models} />
    <div className="dashboard-grid three-two deferred">
      <Panel eyebrow="PRECISION–RECALL" title="测试集 PR 曲线"><p className="panel-description">事件稀缺时，比准确率更能反映预警价值</p><div className="chart-xl"><ResponsiveContainer width="100%" height="100%"><LineChart margin={{ top: 12, right: 12, bottom: 6, left: -10 }}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="recall" type="number" domain={[0, 1]} tick={{ fill: 'var(--muted)', fontSize: 11 }} /><YAxis dataKey="precision" type="number" domain={[0, 1]} tick={{ fill: 'var(--muted)', fontSize: 11 }} /><Tooltip formatter={(value) => [formatNumber(Number(value)), 'Precision']} labelFormatter={(label) => `Recall ${formatNumber(Number(label))}`} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10 }} />{data.models.map((model) => <Line key={model.name} data={data.curves[model.name]} dataKey="precision" name={modelNames[model.name]} stroke={modelColors[model.name]} strokeWidth={model.name === 'xgboost' ? 3 : 2} dot={false} type="monotone" />)}</LineChart></ResponsiveContainer></div><div className="chart-legend">{data.models.map((model) => <span key={model.name}><i style={{ background: modelColors[model.name] }} />{modelNames[model.name]}</span>)}</div></Panel>
      <Panel eyebrow="METRIC EXPLORER" title="指标探索"><div className="segmented-control" aria-label="选择对比指标">{(Object.keys(metricLabels) as MetricKey[]).map((key) => <button key={key} aria-pressed={metric === key} className={metric === key ? 'selected' : ''} onClick={() => setMetric(key)}>{metricLabels[key]}</button>)}</div><div className="chart-lg"><ResponsiveContainer width="100%" height="100%"><BarChart data={bars} margin={{ top: 22, left: -20 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="display" tick={{ fill: 'var(--muted)', fontSize: 10 }} interval={0} /><YAxis domain={[0, 1]} tick={{ fill: 'var(--muted)', fontSize: 11 }} /><Tooltip formatter={(value) => [formatNumber(Number(value)), metricLabels[metric]]} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)' }} /><Bar dataKey="value" radius={[6, 6, 0, 0]}>{bars.map((item) => <Cell key={item.name} fill={modelColors[item.name]} />)}</Bar></BarChart></ResponsiveContainer></div></Panel>
    </div>
    <Panel eyebrow="OUT-OF-TIME EVALUATION" title="完整测试指标" className="deferred"><div className="table-scroll"><table><caption className="visually-hidden">四类模型测试集指标</caption><thead><tr><th scope="col">模型</th><th scope="col">PR-AUC</th><th scope="col">ROC-AUC</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th><th scope="col">FAR</th><th scope="col">阈值</th><th scope="col">TP / FP / FN</th></tr></thead><tbody>{data.models.map((model) => <tr key={model.name} className={model.name === 'xgboost' ? 'highlight-row' : ''}><th scope="row"><span className="table-model-dot" style={{ background: modelColors[model.name] }} />{modelNames[model.name]}</th>{(['pr_auc', 'roc_auc', 'precision', 'recall', 'f1', 'false_alarm_rate', 'threshold'] as const).map((key) => <td key={key}>{formatNumber(model.test[key] as Metrics[typeof key])}</td>)}<td className="confusion-cell"><span>{model.test.tp}</span> / <span>{model.test.fp}</span> / <span>{model.test.fn}</span></td></tr>)}</tbody></table></div><p className="table-note">TP：成功预警 · FP：误报 · FN：漏报。指标计算基于验证集选定的固定阈值。</p></Panel>
  </div>
}
