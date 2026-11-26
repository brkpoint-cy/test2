import { useCallback, useEffect, useMemo, useState } from 'react'
import { Crosshair, Gauge, SlidersHorizontal } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useRemoteData } from '../hooks/useRemoteData'
import { ErrorState, LoadingState, Panel, formatNumber, modelColors, modelNames } from './ui'
import type { ModelResult } from '../types'

export default function ThresholdLab({ models }: { models: ModelResult[] }) {
  const [model, setModel] = useState('xgboost')
  const [partition, setPartition] = useState<'validation' | 'test'>('test')
  const [index, setIndex] = useState(71)
  const loader = useCallback(() => api.thresholdAnalysis(model, partition), [model, partition])
  const { data, error, retry } = useRemoteData(loader, { cacheKey: `threshold:${model}:${partition}` })
  useEffect(() => {
    if (data) setIndex(data.points.reduce((best, point, i) => Math.abs(point.threshold - data.validation_threshold) < Math.abs(data.points[best].threshold - data.validation_threshold) ? i : best, 0))
  }, [data])
  const point = data?.points[index]
  const curve = useMemo(() => data?.points.map((item) => ({ ...item, percent: item.threshold * 100 })), [data])
  if (error) return <ErrorState message={error} retry={retry} />
  if (!data || !point) return <LoadingState label="正在生成 101 个真实阈值评估点" />
  return <Panel eyebrow="INTERACTIVE THRESHOLD LAB" title="拖动阈值，看见模型取舍" className="threshold-lab">
    <div className="threshold-toolbar"><div className="model-pills" aria-label="选择模型">{models.map((item) => <button key={item.name} aria-pressed={model === item.name} className={model === item.name ? 'active' : ''} onClick={() => setModel(item.name)}><i style={{ background: modelColors[item.name] }} />{modelNames[item.name]}</button>)}</div><div className="segmented-control compact" aria-label="选择数据分区"><button className={partition === 'validation' ? 'selected' : ''} aria-pressed={partition === 'validation'} onClick={() => setPartition('validation')}>验证集</button><button className={partition === 'test' ? 'selected' : ''} aria-pressed={partition === 'test'} onClick={() => setPartition('test')}>测试集</button></div></div>
    <div className="threshold-grid"><div className="threshold-control"><div className="threshold-value"><span><SlidersHorizontal size={16} />决策阈值</span><strong>{point.threshold.toFixed(2)}</strong></div><label htmlFor="threshold-slider">在 0–1 之间调整预警概率阈值</label><input id="threshold-slider" className="interactive-range" type="range" min="0" max="100" value={index} onChange={(event) => setIndex(Number(event.target.value))} style={{ '--range-progress': `${index}%` } as React.CSSProperties} /><div className="range-labels"><span>0.00 · 更多预警</span><span>1.00 · 更少预警</span></div><div className="threshold-baseline"><Crosshair size={14} />验证集选定阈值 {data.validation_threshold.toFixed(3)}<button onClick={() => setIndex(Math.round(data.validation_threshold * 100))}>恢复</button></div></div>
      <div className="threshold-live-metrics"><article><span>Precision</span><strong>{formatNumber(point.precision)}</strong><small>预警有多少正确</small></article><article><span>Recall</span><strong>{formatNumber(point.recall)}</strong><small>事件有多少被找到</small></article><article><span>F1</span><strong>{formatNumber(point.f1)}</strong><small>精确与召回平衡</small></article><article><span>FAR</span><strong>{formatNumber(point.false_alarm_rate)}</strong><small>负例中有多少误报</small></article></div>
      <div className="confusion-matrix"><div className="matrix-label"><Gauge size={15} />实时混淆矩阵</div><div className="matrix-grid"><article className="tn"><span>TN</span><strong>{point.tn}</strong><small>正确排除</small></article><article className="fp"><span>FP</span><strong>{point.fp}</strong><small>误报警报</small></article><article className="fn"><span>FN</span><strong>{point.fn}</strong><small>漏报事件</small></article><article className="tp"><span>TP</span><strong>{point.tp}</strong><small>成功预警</small></article></div></div></div>
    <div className="threshold-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={curve} margin={{ top: 12, right: 15, left: -20 }}><defs><linearGradient id="f1Fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={modelColors[model]} stopOpacity={0.25} /><stop offset="1" stopColor={modelColors[model]} stopOpacity={0.01} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="percent" type="number" domain={[0, 100]} unit="%" tick={{ fill: 'var(--muted)', fontSize: 10 }} /><YAxis domain={[0, 1]} tick={{ fill: 'var(--muted)', fontSize: 10 }} /><Tooltip formatter={(value) => [formatNumber(Number(value)), 'F1']} labelFormatter={(label) => `阈值 ${(Number(label) / 100).toFixed(2)}`} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)' }} /><ReferenceLine x={point.threshold * 100} stroke={modelColors[model]} strokeWidth={2} strokeDasharray="4 3" /><Area type="monotone" dataKey="f1" stroke={modelColors[model]} strokeWidth={2.5} fill="url(#f1Fill)" dot={false} /></AreaChart></ResponsiveContainer></div>
  </Panel>
}
