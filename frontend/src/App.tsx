import { useEffect, useState } from 'react'
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

  // "Try a sample" from the home page: wait until the check for an earlier chat is over, then start it once.
  const { phase, restoring, startSample } = session
  useEffect(() => {
    if (route !== 'sample' || restoring) return
    if (phase !== 'uploading') void startSample()
    window.location.replace('#/app')
  }, [route, restoring, phase, startSample])

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
        onLogout={auth.logout}
        onSelectBook={(jobId) => {
          void session.openJob(jobId)
          go('app')
        }}
        onDeleteBook={auth.deleteBook}
      />
      {route === 'home' ? (
        <div className="home-scroll">
          <Home onStart={() => go('app')} onSample={() => go('sample')} />
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
        onLogin={auth.login}
        onSignup={auth.signup}
      />
    </div>
  )
}
