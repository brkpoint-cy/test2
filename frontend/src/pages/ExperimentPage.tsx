import { useCallback, useEffect, useRef, useState } from 'react'
import { Check, ChevronRight, CircleAlert, Clock3, FileInput, LoaderCircle, Play, Settings2 } from 'lucide-react'
import { api } from '../api'
import type { DashboardData, ExperimentRequest, ExperimentStatus } from '../types'
import { PageHeader, Panel, SourceBadge } from '../components/ui'

export default function ExperimentPage({ data, onCompleted }: { data: DashboardData | null; onCompleted: () => void }) {
  const [form, setForm] = useState<ExperimentRequest>({ air_path: 'data/demo/air_quality.csv', weather_path: 'data/demo/weather.csv', data_source: 'synthetic', lookback: 48, horizon: 6, pm25_threshold: 75, epochs: 3, xgb_estimators: 140 })
  const [status, setStatus] = useState<ExperimentStatus>({ run_id: null, status: 'idle', message: '配置完成后即可启动', output: null })
  const [statusReady, setStatusReady] = useState(false)
  const [transportError, setTransportError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const previousStatus = useRef(status.status)
  const requestGeneration = useRef(0)

  const refresh = useCallback(async () => {
    const generation = ++requestGeneration.current
    try {
      const next = await api.experimentStatus()
      if (generation === requestGeneration.current) {
        setStatus(next)
        setStatusReady(true)
        setTransportError('')
      }
    } catch (reason) {
      if (generation === requestGeneration.current) setTransportError(reason instanceof Error ? reason.message : '状态连接失败，正在重试')
    }
  }, [])
  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => {
    if (!['queued', 'running'].includes(status.status)) return
    const timer = window.setInterval(() => { void refresh() }, 1200)
    return () => window.clearInterval(timer)
  }, [status.status, refresh])
  useEffect(() => {
    if (status.status === 'complete' && previousStatus.current !== 'complete') onCompleted()
    previousStatus.current = status.status
  }, [status.status, onCompleted])

  const updateNumber = (key: keyof ExperimentRequest, value: string) => setForm((current) => ({ ...current, [key]: Number(value) }))
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setTransportError('')
    const generation = ++requestGeneration.current
    try {
      const next = await api.startExperiment(form)
      if (generation === requestGeneration.current) {
        setStatus(next)
        setStatusReady(true)
      }
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : '启动失败'
      if (message.includes('已有实验')) await refresh()
      else setTransportError(message)
    } finally { setSubmitting(false) }
  }
  const running = ['queued', 'running'].includes(status.status)
  const formDisabled = running || submitting || !statusReady
  return <div className="page-stack">
    <PageHeader eyebrow="EXPERIMENT RUNNER / 06" title="把下一次研究，变成可复现实验。" description="参数提交给 Python 流水线；后台依次完成清洗、样本构造、四模型训练、评估和报告。" action={data ? <SourceBadge source={data.data_source} /> : undefined} />
    {transportError && <div className="transport-error" role="alert"><CircleAlert size={17} /><span>{transportError}</span><button onClick={() => void refresh()}>重新连接</button></div>}
    <div className="experiment-layout">
      <Panel eyebrow="EXPERIMENT CONFIGURATION" title="实验配置"><form className="experiment-form" onSubmit={submit}>
        <fieldset disabled={formDisabled}><legend><FileInput size={17} />数据输入</legend><label htmlFor="air-path">空气质量 CSV 路径</label><input id="air-path" required value={form.air_path} onChange={(event) => setForm({ ...form, air_path: event.target.value })} /><p className="field-hint">项目目录内文件，需包含 time 与 PM2.5 字段</p><label htmlFor="weather-path">气象 CSV 路径</label><input id="weather-path" value={form.weather_path ?? ''} onChange={(event) => setForm({ ...form, weather_path: event.target.value || null })} /><p className="field-hint">留空则仅使用空气污染特征</p><label htmlFor="data-source">数据来源声明</label><select id="data-source" value={form.data_source} onChange={(event) => setForm({ ...form, data_source: event.target.value as 'observed' | 'synthetic' })}><option value="synthetic">合成 / 演示数据</option><option value="observed">真实观测数据</option></select><p className="field-hint">请如实选择；该声明会显示在所有实验结果中</p></fieldset>
        <fieldset disabled={formDisabled}><legend><Settings2 size={17} />任务与模型</legend><div className="form-grid"><div><label htmlFor="lookback">历史输入窗口（小时）</label><input id="lookback" type="number" min={6} max={168} required value={form.lookback} onChange={(event) => updateNumber('lookback', event.target.value)} /></div><div><label htmlFor="horizon">预测提前量（小时）</label><input id="horizon" type="number" min={1} max={48} required value={form.horizon} onChange={(event) => updateNumber('horizon', event.target.value)} /></div><div><label htmlFor="threshold">PM2.5 事件阈值</label><input id="threshold" type="number" min={1} max={500} required value={form.pm25_threshold} onChange={(event) => updateNumber('pm25_threshold', event.target.value)} /></div><div><label htmlFor="epochs">深度模型训练轮数</label><input id="epochs" type="number" min={1} max={50} required value={form.epochs} onChange={(event) => updateNumber('epochs', event.target.value)} /></div><div><label htmlFor="steps">XGBoost 树数量</label><input id="steps" type="number" min={20} max={500} required value={form.xgb_estimators} onChange={(event) => updateNumber('xgb_estimators', event.target.value)} /></div></div></fieldset>
        <div className="form-notice"><CircleAlert size={17} /><p>请先固定事件定义，再运行实验。不要根据测试集结果反复选择阈值或提前量。</p></div>
        <button className="button primary submit-experiment" type="submit" disabled={formDisabled}>{running ? <LoaderCircle className="spin" size={17} /> : <Play size={17} fill="currentColor" />}{running ? '实验正在运行' : statusReady ? '启动 Python 实验' : '正在连接后端'}<ChevronRight size={17} /></button>
      </form></Panel>
      <aside className="run-sidebar"><Panel eyebrow="RUN STATUS" title="运行状态"><div className={`run-status ${status.status}`} role="status" aria-live="polite"><span className="run-status-icon">{status.status === 'complete' ? <Check size={26} /> : status.status === 'failed' ? <CircleAlert size={26} /> : running ? <LoaderCircle className="spin" size={26} /> : <Clock3 size={26} />}</span><strong>{{ idle: '等待配置', queued: '已进入队列', running: '正在计算', complete: '运行完成', failed: '运行失败' }[status.status]}</strong><p>{status.message}</p>{status.run_id && <code>RUN #{status.run_id}</code>}</div><ol className="run-steps">{['数据质量与时间对齐', '无泄漏窗口构造', '四模型训练与验证', '测试评估与报告发布'].map((label, index) => <li key={label} className={status.status === 'complete' ? 'done' : running && index === 2 ? 'current' : ''}><span>{status.status === 'complete' ? <Check size={13} /> : index + 1}</span>{label}</li>)}</ol>{status.output && <div className="run-output"><span>产物目录</span><code>{status.output}</code></div>}</Panel><div className="compute-note"><span className="status-dot" /><div><strong>全部计算留在 Python</strong><p>React 不参与数据清洗、特征工程、训练或指标计算。</p></div></div></aside>
    </div>
  </div>
}
