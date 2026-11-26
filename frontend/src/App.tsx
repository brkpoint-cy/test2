import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import {
  Activity, BarChart3, BrainCircuit, ChevronRight, Command as CommandIcon, Database, FlaskConical,
  LayoutDashboard, Menu, Moon, Play, Sun, TriangleAlert, X,
} from 'lucide-react'
import { api } from './api'
import { useRemoteData } from './hooks/useRemoteData'
import { usePageNavigation, interceptNavigation, pagePaths } from './hooks/usePageNavigation'
import { useColorScheme } from './hooks/useColorScheme'
import { ErrorState, LoadingState, SourceBadge } from './components/ui'
import ErrorBoundary from './components/ErrorBoundary'
import OverviewPage from './pages/OverviewPage'
import ExperimentPage from './pages/ExperimentPage'
import CommandPalette from './components/CommandPalette'
import type { PageId } from './types'

// 路由级代码分割：非首屏页面按需加载（modern-web-guidance performance）。
const DataPage = lazy(() => import('./pages/DataPage'))
const ModelsPage = lazy(() => import('./pages/ModelsPage'))
const XgbPage = lazy(() => import('./pages/XgbPage'))
const CasesPage = lazy(() => import('./pages/CasesPage'))
const PlaygroundPage = lazy(() => import('./pages/PlaygroundPage'))

const navigation = [
  { id: 'overview' as const, label: '研究总览', icon: LayoutDashboard, group: '研究工作台' },
  { id: 'data' as const, label: '数据洞察', icon: Database, group: '研究工作台' },
  { id: 'models' as const, label: '模型对照', icon: BarChart3, group: '研究工作台' },
  { id: 'xgboost' as const, label: 'XGBoost 实验室', icon: BrainCircuit, group: '模型与实验' },
  { id: 'playground' as const, label: '情景推演', icon: FlaskConical, group: '模型与实验' },
  { id: 'cases' as const, label: '误差案例', icon: TriangleAlert, group: '模型与实验' },
  { id: 'experiment' as const, label: '运行实验', icon: FlaskConical, group: '模型与实验' },
]

const pageTitles: Record<PageId, string> = {
  overview: '研究总览', data: '数据洞察', models: '模型对照', xgboost: 'XGBoost 实验室', playground: '情景推演', cases: '误差案例', experiment: '运行实验',
}

/**
 * 移动端导航抽屉（modern-web-guidance navigation-drawer 的 sidebar 变体）。
 * 桌面端 aside 是普通侧栏；移动端通过 popover="manual" 提升到顶层，
 * 打开/关闭由横向 scroll-snap 滚动驱动，IntersectionObserver 是状态的唯一事实来源。
 */
function useNavigationDrawer(isMobile: boolean) {
  const sidebarRef = useRef<HTMLElement>(null)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const workspaceRef = useRef<HTMLDivElement>(null)
  const openRef = useRef(false)
  const scrollerRef = useRef<HTMLElement | null>(null)

  const closeDrawer = useCallback(() => {
    const scroller = scrollerRef.current
    if (!openRef.current || !scroller) return
    // 只滚动回关闭位；hidePopover 由观察者在 sheet 完全离屏后触发，滑出动画才可见。
    scroller.scrollTo({ left: scroller.offsetWidth, behavior: 'auto' })
  }, [])

  useEffect(() => {
    const sidebar = sidebarRef.current
    if (!isMobile || !sidebar) return
    const scroller = sidebar.querySelector<HTMLElement>('.drawer-scroller')
    const sheet = sidebar.querySelector<HTMLElement>('.drawer-sheet')
    if (!scroller || !sheet) return
    scrollerRef.current = scroller

    const handleOpened = () => {
      openRef.current = true
      menuButtonRef.current?.setAttribute('aria-expanded', 'true')
    }
    const handleClosed = () => {
      // 观察者初始回调也会报告「关闭」，只有确实打开过才执行收尾。
      if (!openRef.current) return
      openRef.current = false
      sidebar.hidePopover()
      if (workspaceRef.current) workspaceRef.current.inert = false
      sidebar.removeAttribute('aria-modal')
      menuButtonRef.current?.setAttribute('aria-expanded', 'false')
      menuButtonRef.current?.focus()
    }

    // 「sheet 是否可见」是抽屉状态的唯一事实来源：滑动、程序滚动、捕捉点落定都会汇聚到这里。
    const visibleThreshold = 1 / window.innerWidth
    const observer = new IntersectionObserver((entries) => {
      const entry = entries.at(-1)
      if (!entry) return
      if (entry.intersectionRatio < visibleThreshold) handleClosed()
      if (entry.intersectionRatio === 1) handleOpened()
    }, { root: sidebar, threshold: [visibleThreshold, 1] })
    observer.observe(sheet)

    // 不支持滚动驱动动画时，用 scroll 监听回写 --drawer-backdrop。
    const handleScrollFallback = !CSS.supports('animation-timeline', 'scroll()')
      ? () => sidebar.style.setProperty('--drawer-backdrop', String(1 - scroller.scrollLeft / sheet.offsetWidth))
      : null
    if (handleScrollFallback) scroller.addEventListener('scroll', handleScrollFallback)

    // Light-dismiss：点击 sheet 之外（遮罩区）关闭。
    const handleClick = (event: MouseEvent) => {
      if (openRef.current && !sheet.contains(event.target as Node)) closeDrawer()
    }
    // popover="manual" 不处理 Escape，需要自行监听。
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeDrawer()
    }
    sidebar.addEventListener('click', handleClick)
    document.addEventListener('keydown', handleKeydown)
    return () => {
      observer.disconnect()
      if (handleScrollFallback) scroller.removeEventListener('scroll', handleScrollFallback)
      sidebar.removeEventListener('click', handleClick)
      document.removeEventListener('keydown', handleKeydown)
      handleClosed()
    }
  }, [isMobile, closeDrawer])

  const openDrawer = useCallback(async () => {
    const sidebar = sidebarRef.current
    const scroller = scrollerRef.current
    if (!sidebar || !scroller) return
    sidebar.showPopover()
    // popover 非模态，手动完成模态职责：页面其余部分 inert + aria-modal。
    if (workspaceRef.current) workspaceRef.current.inert = true
    sidebar.setAttribute('aria-modal', 'true')
    if (!CSS.supports('scroll-initial-target', 'nearest')) {
      // 无 scroll-initial-target 的浏览器：先跳到关闭位，等两帧提交后再滑入。
      scroller.scrollTo({ left: scroller.offsetWidth, behavior: 'instant' })
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    }
    scroller.scrollTo({ left: 0, behavior: 'auto' })
  }, [])

  const navigateFromDrawer = useCallback(() => {
    closeDrawer()
  }, [closeDrawer])

  return { sidebarRef, menuButtonRef, workspaceRef, openDrawer, closeDrawer: navigateFromDrawer }
}

export default function App() {
  const { page, navigate } = usePageNavigation()
  const { scheme, toggle } = useColorScheme()
  const [commandOpen, setCommandOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 900px)').matches)
  const { sidebarRef, menuButtonRef, workspaceRef, openDrawer, closeDrawer } = useNavigationDrawer(isMobile)
  const loader = useCallback(api.dashboard, [])
  const { data, error, retry } = useRemoteData(loader)

  useEffect(() => {
    const media = window.matchMedia('(max-width: 900px)')
    const update = () => setIsMobile(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen((open) => !open)
      }
    }
    document.addEventListener('keydown', handleShortcut)
    return () => document.removeEventListener('keydown', handleShortcut)
  }, [])
  useEffect(() => {
    document.title = `${pageTitles[page]} | AeriScope 澄空`
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [page])

  const go = useCallback((target: PageId) => {
    closeDrawer()
    setCommandOpen(false)
    navigate(target)
  }, [closeDrawer, navigate])

  return <div className="app-shell">
    <a className="skip-link" href="#content">跳转到主要内容</a>
    <aside
      id="primary-sidebar"
      ref={sidebarRef}
      className="sidebar"
      popover={isMobile ? 'manual' : undefined}
      role={isMobile ? 'dialog' : undefined}
      aria-label={isMobile ? '导航抽屉' : undefined}
    >
      <div className="drawer-scroller">
        <div className="drawer-sheet">
          <div className="brand">
            <div className="brand-mark"><Activity size={25} strokeWidth={2.2} /></div>
            <div><strong>AeriScope</strong><span>澄空 · 环境智能研究</span></div>
            <button className="icon-button mobile-close" aria-label="关闭导航" onClick={closeDrawer} autoFocus={isMobile}><X size={19} /></button>
          </div>
          <div className="project-chip"><span className="project-letter">CC</span><div><strong>长春冬季污染预警</strong><span>PM2.5 · XGBOOST RESEARCH</span></div></div>
          <nav aria-label="主导航">
            {['研究工作台', '模型与实验'].map((group) => <div className="nav-group" key={group}>
              <span className="nav-group-label">{group}</span>
              <ul role="list">{navigation.filter((item) => item.group === group).map((item) => {
                const Icon = item.icon
                return <li key={item.id}><a href={pagePaths[item.id]} className={page === item.id ? 'active' : ''} aria-current={page === item.id ? 'page' : undefined} onClick={(event) => interceptNavigation(event, item.id, go)}>
                  <Icon size={18} /><span>{item.label}</span>{page === item.id && <ChevronRight className="nav-arrow" size={15} />}
                </a></li>
              })}</ul>
            </div>)}
          </nav>
          <div className="engine-card"><div><span className="status-dot" />Python 计算引擎</div><p>数据处理 · 机器学习 · 统计评估</p><span>PyTorch / XGBoost</span></div>
          <footer className="sidebar-footer">AERISCOPE LAB <span>v1.0</span></footer>
        </div>
      </div>
    </aside>

    <div className="workspace" ref={workspaceRef}>
      <header className="topbar">
        <div className="topbar-left"><button ref={menuButtonRef} className="icon-button menu-button" aria-label="打开导航" aria-expanded="false" aria-controls="primary-sidebar" onClick={() => void openDrawer()}><Menu size={20} /></button><span className="breadcrumb">长春项目 <ChevronRight size={14} /> <strong>{pageTitles[page]}</strong></span></div>
        <div className="topbar-actions">
          {data && <SourceBadge source={data.data_source} />}
          <button className="command-trigger" aria-label="打开命令面板（Ctrl+K）" onClick={() => setCommandOpen(true)}><CommandIcon size={15} /><span>⌘ K</span></button>
          <button className="icon-button" aria-label={scheme === 'light' ? '切换到深色主题' : '切换到浅色主题'} onClick={toggle}>{scheme === 'light' ? <Moon size={18} /> : <Sun size={18} />}</button>
          <a className="button primary run-button" href={pagePaths.experiment} onClick={(event) => interceptNavigation(event, 'experiment', go)}><Play size={15} fill="currentColor" />新建实验</a>
        </div>
      </header>
      <main id="content" tabIndex={-1}>
        <ErrorBoundary>
          <Suspense fallback={<LoadingState />}>
            {page === 'experiment' ? <ExperimentPage data={data} onCompleted={retry} />
              : page === 'overview' ? (error ? <ErrorState message={error} retry={retry} /> : !data ? <LoadingState /> : <OverviewPage data={data} onNavigate={go} />)
              : page === 'xgboost' ? (error ? <ErrorState message={error} retry={retry} /> : !data ? <LoadingState /> : <XgbPage data={data} />)
              : page === 'data' ? <DataPage />
              : page === 'models' ? <ModelsPage />
              : page === 'playground' ? <PlaygroundPage />
              : page === 'cases' ? <CasesPage />
              : null}
          </Suspense>
        </ErrorBoundary>
      </main>
      <footer className="workspace-footer"><span>AeriScope · 仅供研究，不用于现实公共预警</span><a href="/api/report" download>导出 Markdown 报告</a></footer>
    </div>
    <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} onNavigate={go} onToggleTheme={toggle} theme={scheme} />
  </div>
}
