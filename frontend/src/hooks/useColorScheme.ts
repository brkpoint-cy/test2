import { useCallback, useEffect, useState } from 'react'

type Scheme = 'light' | 'dark'

const STORAGE_KEY = 'aeriscope-theme'

function colorSchemeMeta(): HTMLMetaElement | null {
  return document.querySelector('meta[name="color-scheme"]')
}

function storedScheme(): Scheme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

function systemScheme(): Scheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** 当前实际渲染的配色：用户覆盖优先，否则跟随系统。 */
function renderedScheme(): Scheme {
  return storedScheme() ?? systemScheme()
}

/**
 * modern-web-guidance dark-mode-toggle 的两态切换：
 * 界面只暴露「系统默认（显示为当前解析值）」与「与当前相反」两个状态；
 * 目标配色与系统一致时删除本地存储（回到跟随系统），不一致时才持久化覆盖。
 */
export function useColorScheme() {
  const [scheme, setScheme] = useState<Scheme>(renderedScheme)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const sync = () => setScheme(renderedScheme())
    // 系统配色变化、其他标签页写入存储时保持同步。
    media.addEventListener('change', sync)
    window.addEventListener('storage', sync)
    return () => {
      media.removeEventListener('change', sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const toggle = useCallback(() => {
    // 用户意图是「切换到当前看到的反面」，而非系统默认的反面。
    const target: Scheme = renderedScheme() === 'dark' ? 'light' : 'dark'
    try {
      if (target === systemScheme()) localStorage.removeItem(STORAGE_KEY)
      else localStorage.setItem(STORAGE_KEY, target)
    } catch {
      // 存储不可用（如站点数据被禁用）时仍应用本次切换，只是无法持久化。
    }
    const meta = colorSchemeMeta()
    if (meta) meta.content = storedScheme() ?? 'light dark'
    setScheme(target)
  }, [])

  return { scheme, toggle }
}
