import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { Activity, ArrowLeft, ArrowRight, Cloud, Droplets, FlaskConical, Gauge, RotateCcw, Thermometer, Waves, Wind } from 'lucide-react'
import { api } from '../api'
import { useRemoteData } from '../hooks/useRemoteData'
import { ErrorState, LoadingState, PageHeader, Panel, SourceBadge } from '../components/ui'
import type { SimulationResult, SimulationValues } from '../types'

function ScenarioSlider({ id, label, value, min, max, step, unit, icon, original, onChange }: {
  id: string
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  icon: ReactNode
  original: number
  onChange: (value: number) => void
}) {
  const progress = (value - min) / (max - min) * 100
  return <div className="scenario-slider"><div className="scenario-label"><label htmlFor={id}>{icon}{label}</label><strong>{value.toFixed(step < 1 ? 1 : 0)}<small>{unit}</small></strong></div><input id={id} className="interactive-range" type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} style={{ '--range-progress': `${progress}%` } as CSSProperties} /><div className="scenario-range"><span>{min}{unit}</span><span>原值 {original.toFixed(1)}{unit}</span><span>{max}{unit}</span></div></div>
}

function ProbabilityGauge({ score, baseline, threshold, loading }: { score: number; baseline: number; threshold: number; loading: boolean }) {
  const delta = score - baseline
  return <div className="probability-wrap"><div className={`probability-gauge ${loading ? 'loading' : ''}`} style={{ '--probability': `${score * 100}%` } as CSSProperties}><div><span>事件概率</span><strong>{(score * 100).toFixed(1)}<small>%</small></strong><em>{score >= threshold ? '达到预警阈值' : '低于预警阈值'}</em></div></div><div className={`probability-delta ${delta >= 0 ? 'up' : 'down'}`}><Activity size={15} />较原情景 {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)} 个百分点</div><div className="probability-scale"><span>0%</span><span>验证阈值 {(threshold * 100).toFixed(1)}%</span><span>100%</span></div></div>
}

export default function PlaygroundPage() {
  const [sampleIndex, setSampleIndex] = useState(0)
  const loader = useCallback(() => api.simulationContext(sampleIndex), [sampleIndex])
  const { data, error, retry } = useRemoteData(loader)
  const [values, setValues] = useState<SimulationValues | null>(null)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [simulating, setSimulating] = useState(false)
  const [simulationError, setSimulationError] = useState('')
  const generation = useRef(0)

  useEffect(() => {
    if (data) {
      setValues(data.values)
      setResult(null)
      setSimulationError('')
    }
  }, [data])
  useEffect(() => {
    if (!values || !data) return
    const currentGeneration = ++generation.current
    setSimulating(true)
    const timer = window.setTimeout(() => {
      api.simulate(sampleIndex, values).then((next) => {
        if (currentGeneration === generation.current) {
          setResult(next)
          setSimulationError('')
        }
      }).catch((reason: unknown) => {
        if (currentGeneration === generation.current) setSimulationError(reason instanceof Error ? reason.message : '推演失败')
      }).finally(() => {
        if (currentGeneration === generation.current) setSimulating(false)
      })
    }, 180)
    return () => window.clearTimeout(timer)
  }, [values, data, sampleIndex])

  if (error) return <ErrorState message={error} retry={retry} />
  if (!data) return <LoadingState label="正在载入真实测试样本与 XGBoost" />
  const score = result?.score ?? data.baseline_score
  const update = (key: keyof SimulationValues) => (value: number) => setValues((current) => current ? { ...current, [key]: value } : current)
  const reset = () => {
    generation.current += 1
    setValues(data.values)
    setResult(null)
  }
  return <div className="page-stack">
    <PageHeader eyebrow="INTERACTIVE WHAT-IF / 05" title="拖动现实，观察预警如何变化。" description="选取一个真实测试窗口，只改变当前时刻变量；Python 使用已训练的 XGBoost 实时计算，而不是在浏览器中伪造预测。" action={<SourceBadge source={data.data_source} />} />
    <div className="playground-grid">
      <Panel eyebrow="SCENARIO CONTROLS" title="情景变量" className="scenario-panel">
        <div className="sample-selector"><div><span>测试样本</span><strong>#{sampleIndex + 1}<small> / {data.sample_count}</small></strong></div><div className="sample-buttons"><button aria-label="上一个测试样本" disabled={sampleIndex === 0} onClick={() => setSampleIndex((value) => Math.max(0, value - 1))}><ArrowLeft size={16} /></button><button aria-label="下一个测试样本" disabled={sampleIndex >= data.sample_count - 1} onClick={() => setSampleIndex((value) => Math.min(data.sample_count - 1, value + 1))}><ArrowRight size={16} /></button></div></div>
        <label className="sample-range-label" htmlFor="sample-range">在测试集中快速定位</label><input id="sample-range" className="interactive-range" type="range" min={0} max={data.sample_count - 1} value={sampleIndex} onChange={(event) => setSampleIndex(Number(event.target.value))} style={{ '--range-progress': `${sampleIndex / (data.sample_count - 1) * 100}%` } as CSSProperties} />
        <div className="sample-context"><span>{data.time.replace('T', ' ')}</span><strong className={data.actual ? 'event' : 'normal'}>{data.actual ? '未来实际发生事件' : '未来实际未发生事件'}</strong></div>
        {values && <div className="scenario-sliders"><ScenarioSlider id="scenario-pm25" label="当前 PM2.5" value={values.pm25} original={data.values.pm25} min={0} max={250} step={1} unit=" μg/m³" icon={<Cloud size={16} />} onChange={update('pm25')} /><ScenarioSlider id="scenario-temperature" label="当前温度" value={values.temperature} original={data.values.temperature} min={-35} max={40} step={0.5} unit="°C" icon={<Thermometer size={16} />} onChange={update('temperature')} /><ScenarioSlider id="scenario-humidity" label="相对湿度" value={values.humidity} original={data.values.humidity} min={0} max={100} step={1} unit="%" icon={<Droplets size={16} />} onChange={update('humidity')} /><ScenarioSlider id="scenario-wind" label="当前风速" value={values.wind_speed} original={data.values.wind_speed} min={0} max={15} step={0.1} unit=" m/s" icon={<Wind size={16} />} onChange={update('wind_speed')} /></div>}
        <button className="button secondary reset-scenario" onClick={reset}><RotateCcw size={15} />恢复原始情景</button>
      </Panel>
      <div className="playground-results">
        <Panel eyebrow="LIVE MODEL RESPONSE" title="XGBoost 实时响应" className="probability-panel"><ProbabilityGauge score={score} baseline={data.baseline_score} threshold={data.threshold} loading={simulating} />{simulationError && <p className="simulation-error" role="alert">{simulationError}</p>}<div className="prediction-outcome"><span className={`outcome-icon ${score >= data.threshold ? 'warning' : 'safe'}`}><Gauge size={20} /></span><div><span>模型判定</span><strong>{score >= data.threshold ? '未来窗口可能发生污染事件' : '未来窗口可能保持非事件状态'}</strong><p>真实类别仅用于后验比较，不参与本次情景计算</p></div></div></Panel>
        <Panel eyebrow="BASELINE VS SCENARIO" title="原情景与当前推演"><div className="scenario-comparison"><article><span>原始预测概率</span><strong>{(data.baseline_score * 100).toFixed(1)}%</strong><div className="comparison-track"><i style={{ width: `${data.baseline_score * 100}%` }} /></div></article><article><span>当前推演概率</span><strong>{(score * 100).toFixed(1)}%</strong><div className="comparison-track active"><i style={{ width: `${score * 100}%` }} /></div></article></div><div className="scenario-note"><FlaskConical size={18} /><p>这是固定历史特征的模型敏感性分析：只改变当前 PM2.5、温度、湿度和风速，其他污染物、滞后与滚动特征保持不变。它不等于真实天气过程预测，也不证明因果。</p></div><div className="model-proof"><Waves size={16} /><span>Python 推理 · XGBoost 140 棵树 · 训练集标准化器</span>{simulating && <em>计算中</em>}</div></Panel>
      </div>
    </div>
  </div>
}
