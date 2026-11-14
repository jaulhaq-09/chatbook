import { useEffect, useState } from 'react'

export type Route = 'home' | 'app' | 'sample'

function parse(hash: string): Route {
  if (hash.startsWith('#/app/sample')) return 'sample'
  if (hash.startsWith('#/app')) return 'app'
  return 'home'
}

/** Tiny hash router: #/ is the home page, #/app the workspace. No extra dependency, works from any static host. */
export function useRoute(): [Route, (to: 'home' | 'app' | 'sample') => void] {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash))
  useEffect(() => {
    const on = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = (to: 'home' | 'app' | 'sample') => {
    window.location.hash = to === 'home' ? '#/' : to === 'app' ? '#/app' : '#/app/sample'
  }
  return [route, go]
}