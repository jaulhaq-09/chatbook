import type { ThemePref } from '../hooks/useTheme'
import type { Route } from '../hooks/useRoute'
import type { User, UserBook } from '../api/types'
import { UserMenu } from './UserMenu'
import { Icon } from './ui'

interface Props {
  route: Route
  theme: ThemePref
  onTheme: () => void
  user: User | null
  books: UserBook[]
  booksLoading: boolean
  currentJobId?: string | null
  onOpenLogin: () => void
  onOpenSignup: () => void
  onLogout: () => void
  onSelectBook: (jobId: string) => void
  onDeleteBook: (jobId: string) => void
}

export function TopBar({
  route,
  theme,
  onTheme,
  user,
  books,
  booksLoading,
  currentJobId,
  onOpenLogin,
  onOpenSignup,
  onLogout,
  onSelectBook,
  onDeleteBook,
}: Props) {
  const icon = theme === 'light' ? 'sun' : theme === 'dark' ? 'moon' : 'auto'
  const name = theme === 'system' ? 'Match system' : theme === 'light' ? 'Light' : 'Dark'
  const inApp = route !== 'home'
  return (
    <header className="topbar">
      <a className="brand" href="#/" aria-label="Chatbook home">
        <span className="logo" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="22" height="22">
            <path d="M8 9h16v10H14l-6 5z" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
          </svg>
        </span>
        <span className="brand-name">Chatbook</span>
        <span className="brand-sub">Chats to print-ready PDF</span>
      </a>
      <nav className="topnav" aria-label="Main">
        <a href="#/" className={!inApp ? 'on' : ''}>
          Home
        </a>
        <a href="#/app" className={inApp ? 'on' : ''}>
          Workspace
        </a>
      </nav>

      <div className="topbar-actions">
        <UserMenu
          user={user}
          books={books}
          booksLoading={booksLoading}
          currentJobId={currentJobId}
          onOpenLogin={onOpenLogin}
          onOpenSignup={onOpenSignup}
          onLogout={onLogout}
          onSelectBook={onSelectBook}
          onDeleteBook={onDeleteBook}
        />
        <button
          type="button"
          className="btn ghost theme"
          onClick={onTheme}
          title={`Theme: ${name}`}
          aria-label={`Theme: ${name}. Click to change.`}
        >
          <Icon name={icon} />
          <span>{name}</span>
        </button>
      </div>
    </header>
  )
}
