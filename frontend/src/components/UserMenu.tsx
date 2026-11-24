import { useState, useRef, useEffect } from 'react'
import type { User, UserBook } from '../api/types'

interface Props {
  user: User | null
  books: UserBook[]
  booksLoading: boolean
  currentJobId?: string | null
  onOpenLogin: () => void
  onOpenSignup?: () => void
  onLogout: () => void
  onSelectBook: (jobId: string) => void
  onDeleteBook: (jobId: string) => void
}

export function UserMenu({
  user,
  books,
  booksLoading,
  currentJobId,
  onOpenLogin,
  onLogout,
  onSelectBook,
  onDeleteBook,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    window.addEventListener('mousedown', handleClick)
    return () => window.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  if (!user) {
    return (
      <div className="auth-nav-buttons">
        <button type="button" className="auth-login-link" onClick={onOpenLogin}>
          Log in
        </button>
      </div>
    )
  }

  const initial = (user.name || user.email || 'U')[0].toUpperCase()

  return (
    <div className="user-menu-wrapper" ref={menuRef}>
      <button
        type="button"
        className={`user-pill-btn ${menuOpen ? 'active' : ''}`}
        onClick={() => setMenuOpen(!menuOpen)}
        title={user.email}
      >
        <span className="user-avatar-circle">{initial}</span>
        <span className="user-pill-name">{user.name || user.email.split('@')[0]}</span>
        {books.length > 0 && <span className="user-books-count">{books.length}</span>}
      </button>

      {menuOpen && (
        <div className="user-dropdown-card">
          <div className="user-dropdown-header">
            <div className="user-dropdown-name">{user.name || 'User'}</div>
            <div className="user-dropdown-email">{user.email}</div>
          </div>

          <div className="user-dropdown-section-title">
            <span>My Chatbooks</span>
            {booksLoading && <span className="spinner-inline" />}
          </div>

          <div className="user-books-list">
            {books.length === 0 ? (
              <div className="user-books-empty">
                You haven&apos;t saved any books yet. Upload a WhatsApp export to build your first book!
              </div>
            ) : (
              books.map((b) => {
                const isCurrent = b.id === currentJobId
                return (
                  <div key={b.id} className={`user-book-item ${isCurrent ? 'current' : ''}`}>
                    <div className="user-book-info" onClick={() => {
                      setMenuOpen(false)
                      onSelectBook(b.id)
                    }}>
                      <div className="user-book-title">{b.title || 'Chatbook'}</div>
                      <div className="user-book-meta">
                        {b.message_count ? `${b.message_count.toLocaleString()} messages` : 'In progress'}
                        {b.photo_count ? ` • ${b.photo_count} photos` : ''}
                      </div>
                    </div>
                    <div className="user-book-actions">
                      <button
                        type="button"
                        className="user-book-open-btn"
                        onClick={() => {
                          setMenuOpen(false)
                          onSelectBook(b.id)
                        }}
                      >
                        {isCurrent ? 'Current' : 'Open'}
                      </button>
                      <button
                        type="button"
                        className="user-book-delete-btn"
                        title="Delete book"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (window.confirm(`Delete "${b.title || 'Chatbook'}"?`)) {
                            onDeleteBook(b.id)
                          }
                        }}
                      >
                        &times;
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          <div className="user-dropdown-footer">
            <button
              type="button"
              className="user-logout-btn"
              onClick={() => {
                setMenuOpen(false)
                onLogout()
              }}
            >
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
