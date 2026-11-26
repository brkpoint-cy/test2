import type { ReactNode } from 'react'
import { AlertCircle, ArrowUpRight, Inbox, LoaderCircle, RefreshCw } from 'lucide-react'

export function Panel({ title, eyebrow, action, children, className = '' }: {
  title?: string
  eyebrow?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return <section className={`panel ${className}`}>
    {(title || eyebrow || action) && <header className="panel-header">
      <div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}{title && <h2>{title}</h2>}</div>
      {action}
    </header>}
    {children}
  </section>
}

export function PageHeader({ eyebrow, title, description, action }: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return <header className="page-header">
    <div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>
    {action}
  </header>
}

export function SourceBadge({ source }: { source: string }) {
  return <span className={`source-badge ${source}`}><span className="status-dot" />{source === 'synthetic' ? '合成演示数据' : '真实观测数据'}</span>
}

export function MetricCard({ label, value, suffix, detail, icon, tone = 'teal' }: {
  label: string
  value: string
  suffix?: string
  detail: string
  icon: ReactNode
  tone?: 'teal' | 'coral' | 'blue' | 'gold'
}) {
  return <article className={`metric-card tone-${tone}`}>
    <div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div>
    <div className="metric-value">{value}{suffix && <small>{suffix}</small>}</div>
    <div className="metric-detail">{detail}<ArrowUpRight size={14} aria-hidden="true" /></div>
  </article>
}

export function LoadingState({ label = '正在读取 Python 分析结果' }: { label?: string }) {
  return <div className="state-card"><LoaderCircle className="spin" size={26} /><p>{label}</p><span>数据与统计均在 Python 后端完成</span></div>
}

export function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return <div className="state-card error" role="alert"><AlertCircle size={28} /><h2>暂时无法载入研究结果</h2><p>{message}</p><button className="button secondary" onClick={retry}><RefreshCw size={16} />重新加载</button></div>
}

export function EmptyState({ label }: { label: string }) {
  return <div className="empty-state"><Inbox size={26} /><p>{label}</p></div>
}

export const modelNames: Record<string, string> = {
  persistence: '持续性基线',
  logistic_regression: '逻辑回归',
  lstm: 'LSTM',
  xgboost: 'XGBoost',
}

export const modelColors: Record<string, string> = {
  persistence: '#94a3b8',
  logistic_regression: '#d8905f',
  lstm: '#5587c9',
  xgboost: '#168573',
}

export function formatNumber(value: number | null | undefined, digits = 3) {
  return value == null ? '—' : value.toFixed(digits)
}
