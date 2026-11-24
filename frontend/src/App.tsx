import { useCallback, useEffect, useState } from 'react'
import { AuthModal } from './components/AuthModal'
import { TopBar } from './components/TopBar'
import { useAuth } from './hooks/useAuth'
import { useRoute } from './hooks/useRoute'
import { useSession } from './hooks/useSession'
import { useTheme } from './hooks/useTheme'
import { Home } from './pages/Home'
import { Workspace } from './pages/Workspace'
import type { RenderOptions } from './api/types'
import { loadOptions, saveOptions } from './state/options'

export default function App() {
  const [route, go] = useRoute()
  const [theme, cycleTheme] = useTheme()
  const session = useSession()
  const auth = useAuth()
  const [options, setOptions] = useState<RenderOptions>(() => loadOptions())

  // Remember paper, style and album choices for the next visit.
  useEffect(() => saveOptions(options), [options])

  // Route protection: Workspace requires an authenticated session.
  // If not logged in, redirect to home and prompt login.
  useEffect(() => {
    if (!auth.loading && !auth.user && route !== 'home') {
      go('home')
      auth.openLogin()
    }
  }, [auth.loading, auth.user, route, go, auth])

  // "Try a sample": only for logged-in users; if guest, prompt login first.
  const { phase, restoring, startSample } = session
  useEffect(() => {
    if (route !== 'sample' || restoring) return
    if (!auth.loading && !auth.user) {
      go('home')
      auth.openLogin()
      return
    }
    if (phase !== 'uploading') void startSample()
    window.location.replace('#/app')
  }, [route, restoring, phase, startSample, auth.loading, auth.user, go, auth])

  const handleLogin = useCallback(
    async (email: string, pass: string, jobId?: string | null) => {
      await auth.login(email, pass, jobId)
      go('app')
    },
    [auth, go]
  )

  const handleSignup = useCallback(
    async (email: string, pass: string, name: string, jobId?: string | null) => {
      await auth.signup(email, pass, name, jobId)
      go('app')
    },
    [auth, go]
  )

  const handleLogout = useCallback(async () => {
    await auth.logout()
    await session.reset()
    go('home')
  }, [auth, session, go])

  return (
    <div className="app">
      <TopBar
        route={route}
        theme={theme}
        onTheme={cycleTheme}
        user={auth.user}
        books={auth.books}
        booksLoading={auth.booksLoading}
        currentJobId={session.job?.id}
        onOpenLogin={auth.openLogin}
        onOpenSignup={auth.openSignup}
        onLogout={handleLogout}
        onSelectBook={(jobId) => {
          void session.openJob(jobId)
          go('app')
        }}
        onDeleteBook={auth.deleteBook}
      />
      {route === 'home' || (!auth.user && !auth.loading) ? (
        <div className="home-scroll">
          <Home
            user={auth.user}
            onStart={() => go('app')}
            onSample={() => go('sample')}
            onOpenAuth={(tab) => (tab === 'login' ? auth.openLogin() : auth.openSignup())}
          />
        </div>
      ) : (
        <Workspace session={session} options={options} setOptions={setOptions} />
      )}

      <AuthModal
        open={auth.modalOpen}
        initialTab={auth.modalTab}
        activeJobTitle={session.job?.suggested_title}
        activeJobId={session.job?.id}
        onClose={auth.closeModal}
        onLogin={handleLogin}
        onSignup={handleSignup}
      />
    </div>
  )
}
