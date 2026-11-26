import { useCallback, useState } from 'react'
import { CheckCircle2, CircleX, TriangleAlert } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useRemoteData } from '../hooks/useRemoteData'
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel, SourceBadge } from '../components/ui'

const caseMeta = {
  tp: { title: '成功预警', subtitle: 'TRUE POSITIVE', icon: CheckCircle2, className: 'success' },
  fn: { title: '漏报事件', subtitle: 'FALSE NEGATIVE', icon: CircleX, className: 'danger' },
  fp: { title: '误报警报', subtitle: 'FALSE POSITIVE', icon: TriangleAlert, className: 'warning' },
}

export default function CasesPage() {
  const loader = useCallback(() => api.cases('xgboost'), [])
  const { data, error, retry } = useRemoteData(loader, { cacheKey: 'cases:xgboost' })
  const [active, setActive] = useState<'tp' | 'fn' | 'fp'>('tp')
  if (error) return <ErrorState message={error} retry={retry} />
  if (!data) return <LoadingState label="正在由 Python 选择典型误差案例" />
  const current = data.cases[active]
  const futureStart = current.series.find((point) => point.phase === 'future')?.time
  return <div className="page-stack">
    <PageHeader eyebrow="ERROR DIAGNOSTICS / 05" title="答案之外，更要知道错在哪里。" description="从时间外测试集选取 XGBoost 的成功预警、漏报和误报，回到原始序列审视模型行为。" action={<SourceBadge source={data.data_source} />} />
    <div className="case-tabs" role="group" aria-label="选择误差案例">{(Object.keys(caseMeta) as Array<'tp' | 'fn' | 'fp'>).map((key) => { const meta = caseMeta[key]; const Icon = meta.icon; const item = data.cases[key]; return <button key={key} aria-pressed={active === key} className={`${meta.className} ${active === key ? 'active' : ''}`} onClick={() => setActive(key)}><Icon size={22} /><div><span>{meta.subtitle}</span><strong>{meta.title}</strong></div><b>{item.available ? `${((item.score ?? 0) * 100).toFixed(1)}%` : '—'}</b><small>预测概率</small></button> })}</div>
    {current.available ? <>
      <div className="case-context"><div><span>预测起点</span><strong>{current.time?.replace('T', ' ')}</strong></div><div><span>真实类别</span><strong>{current.actual === 1 ? '未来发生污染事件' : '未来未发生污染事件'}</strong></div><div><span>XGBoost 预测概率</span><strong>{((current.score ?? 0) * 100).toFixed(2)}%</strong></div><div><span>验证集决策阈值</span><strong>{((current.threshold ?? 0) * 100).toFixed(2)}%</strong></div></div>
      <Panel eyebrow={`${caseMeta[active].subtitle} / TEST CASE`} title={`${caseMeta[active].title} · 预测前后序列`} className="deferred"><p className="panel-description">虚线为预测起点，浅色区域为未来预测窗口；红线为研究事件阈值</p><div className="chart-case"><ResponsiveContainer width="100%" height="100%"><AreaChart data={current.series} margin={{ top: 18, right: 24, left: 0 }}><defs><linearGradient id="caseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#168573" stopOpacity={0.26} /><stop offset="1" stopColor="#168573" stopOpacity={0.015} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="time" tickFormatter={(value: string) => value.slice(5, 16).replace('T', ' ')} minTickGap={60} tick={{ fill: 'var(--muted)', fontSize: 11 }} /><YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} unit=" μg" /><Tooltip labelFormatter={(label) => String(label).replace('T', ' ')} formatter={(value) => [Number(value).toFixed(1), 'PM2.5 μg/m³']} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10 }} />{futureStart && <ReferenceArea x1={futureStart} x2={current.series.at(-1)?.time} fill="#d8905f" fillOpacity={0.07} />}<ReferenceLine x={current.time} stroke="var(--text)" strokeDasharray="5 4" label={{ value: '预测起点', fill: 'var(--muted)', fontSize: 11, position: 'insideTopLeft' }} /><ReferenceLine y={data.pm25_threshold} stroke="#d8705f" strokeDasharray="4 4" /><Area type="monotone" dataKey="pm25" stroke="#168573" strokeWidth={2.5} fill="url(#caseFill)" dot={false} /></AreaChart></ResponsiveContainer></div></Panel>
      <section className={`case-interpretation ${caseMeta[active].className}`}><strong>如何阅读这个案例</strong><p>{active === 'tp' ? '预测概率超过验证集阈值，且未来窗口内实际发生污染事件。这是正确命中，不代表每个相似过程都会被识别。' : active === 'fn' ? '未来窗口内实际发生污染事件，但预测概率未达到阈值。应结合气象突变、历史序列和阈值选择分析漏报原因。' : '预测概率超过阈值，但未来窗口没有实际发生事件。应检查当前高污染状态是否让模型过度外推。'}</p></section>
    </> : <EmptyState label={`测试期没有${caseMeta[active].title}案例；不会伪造示例。`} />}
  </div>
}
