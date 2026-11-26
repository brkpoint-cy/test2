import { useCallback, useEffect, useRef, useState } from 'react'
import type { PageId } from '../types'

/** 页面 ID 与 URL 路径的双向映射；'/' 作为总览页的规范路径。 */
export const pagePaths: Record<PageId, string> = {
  overview: '/',
  data: '/data',
  models: '/models',
  xgboost: '/xgboost',
  playground: '/playground',
  cases: '/cases',
  experiment: '/experiment',
}

const pageIds = Object.keys(pagePaths) as PageId[]

function pageFromLocation(): PageId {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const match = pageIds.find((id) => pagePaths[id] === path)
  return match ?? 'overview'
}

const supportsViewTransitions = typeof document !== 'undefined' && 'startViewTransition' in document

/**
 * 平面 SPA 的 History 集成（modern-web-guidance stack-drill-down 的简化版）：
 * - navigate 时 pushState，方向（forward/backward）作为 view-transition 类型；
 * - popstate（浏览器/系统后退前进）恢复对应页面，URL 始终是唯一事实来源；
 * - 深链接与刷新直达对应页面。
 */
export function usePageNavigation() {
  const [page, setPage] = useState<PageId>(pageFromLocation)
  const pageRef = useRef(page)
  pageRef.current = page

  useEffect(() => {
    const initial = pageFromLocation()
    // 为落地条目附加页面标识，后续 pushState / popstate 以此为准。
    window.history.replaceState({ page: initial }, '', pagePaths[initial])
    const handlePopState = (event: PopStateEvent) => {
      const state = event.state as { page?: PageId } | null
      const target = state?.page && pageIds.includes(state.page) ? state.page : pageFromLocation()
      const from = pageIds.indexOf(pageRef.current)
      const to = pageIds.indexOf(target)
      applyPage(target, to >= from ? 'forward' : 'backward')
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const applyPage = useCallback((target: PageId, direction: 'forward' | 'backward') => {
    const update = () => setPage(target)
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (supportsViewTransitions && !reducedMotion) {
      try {
        const startTransition = document.startViewTransition as unknown as (options: { update: () => void; types: string[] }) => { finished: Promise<void> }
        const transition = startTransition({ update, types: [direction] })
        transition.finished.finally(() => document.getElementById('content')?.focus())
        return
      } catch {
        // 某些浏览器不支持带 types 的调用形式，退回无过渡更新。
      }
    }
    update()
    document.getElementById('content')?.focus()
  }, [])

  const navigate = useCallback((target: PageId) => {
    if (target === pageRef.current) return
    const from = pageIds.indexOf(pageRef.current)
    const to = pageIds.indexOf(target)
    window.history.pushState({ page: target }, '', pagePaths[target])
    applyPage(target, to >= from ? 'forward' : 'backward')
  }, [applyPage])

  return { page, navigate }
}

/**
 * 内部锚点的点击拦截：普通左键走 SPA 导航，
 * Ctrl/Cmd/Shift/中键保持浏览器默认行为（新标签/新窗口打开）。
 */
export function interceptNavigation(event: React.MouseEvent<HTMLAnchorElement>, page: PageId, navigate: (page: PageId) => void) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  navigate(page)
}
