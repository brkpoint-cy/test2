import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Command, Moon, Search, Sun } from 'lucide-react'
import { interceptNavigation, pagePaths } from '../hooks/usePageNavigation'
import type { PageId } from '../types'

const commands: Array<{ id: PageId; label: string; hint: string }> = [
  { id: 'overview', label: '研究总览', hint: '核心指标与实验协议' },
  { id: 'data', label: '数据洞察', hint: '序列缩放与气象联动' },
  { id: 'models', label: '模型对照 + 阈值实验室', hint: '实时调整决策阈值' },
  { id: 'xgboost', label: 'XGBoost 实验室', hint: '树模型与特征重要性' },
  { id: 'playground', label: 'XGBoost 情景推演', hint: '交互调整气象与污染水平' },
  { id: 'cases', label: '误差案例', hint: '成功、漏报与误报' },
  { id: 'experiment', label: '运行新实验', hint: '启动 Python 训练流水线' },
]

export default function CommandPalette({ open, onClose, onNavigate, onToggleTheme, theme }: {
  open: boolean
  onClose: () => void
  onNavigate: (page: PageId) => void
  onToggleTheme: () => void
  theme: string
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [query, setQuery] = useState('')
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal()
    if (!open && dialog.current?.open) dialog.current.close()
  }, [open])
  useEffect(() => { if (!open) setQuery('') }, [open])
  const filtered = commands.filter((item) => `${item.label}${item.hint}`.toLowerCase().includes(query.toLowerCase()))
  return <dialog ref={dialog} className="command-dialog" aria-labelledby="command-title" onClose={onClose} onClick={(event) => { if (event.target === dialog.current) onClose() }}>
    <search className="command-search"><Search size={19} /><label id="command-title" className="visually-hidden" htmlFor="command-input">搜索页面与操作</label><input id="command-input" type="search" autoFocus placeholder="搜索页面、实验或操作…" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && filtered[0]) onNavigate(filtered[0].id) }} /><kbd>ESC</kbd></search>
    <div className="command-results">{filtered.map((item, index) => <a key={item.id} href={pagePaths[item.id]} onClick={(event) => interceptNavigation(event, item.id, onNavigate)}><span className="command-index">{String(index + 1).padStart(2, '0')}</span><div><strong>{item.label}</strong><span>{item.hint}</span></div><ArrowRight size={16} /></a>)}{!filtered.length && <p className="command-empty">没有匹配的命令</p>}</div>
    <div className="command-footer"><button onClick={onToggleTheme}>{theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}切换{theme === 'light' ? '深色' : '浅色'}主题</button><span><Command size={13} /> K 快速打开</span></div>
  </dialog>
}
