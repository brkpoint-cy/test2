import { useCallback, useEffect, useState } from 'react'

/**
 * 会话级数据缓存：回访已加载过的页面时直接命中，无需重新请求。
 * 仅用于条目数量固定的 API（区别于无限动态路由，避免内存膨胀）。
 */
const cache = new Map<string, unknown>()

export function useRemoteData<T>(loader: () => Promise<T>, options?: { cacheKey?: string }) {
  const cacheKey = options?.cacheKey
  const [data, setData] = useState<T | null>(() => (cacheKey && cache.has(cacheKey) ? cache.get(cacheKey) as T : null))
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const retry = useCallback(() => {
    if (cacheKey) cache.delete(cacheKey)
    setVersion((value) => value + 1)
  }, [cacheKey])
  useEffect(() => {
    if (cacheKey && version === 0 && cache.has(cacheKey)) return
    let active = true
    if (version === 0) setData(null)
    setError('')
    loader().then((result) => {
      if (active) {
        if (cacheKey) cache.set(cacheKey, result)
        setData(result)
      }
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : '未知错误')
    })
    return () => { active = false }
  }, [loader, version, cacheKey])
  return { data, error, retry }
}
