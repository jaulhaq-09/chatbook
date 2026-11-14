import { useState } from 'react'
import type { FormEvent } from 'react'

interface Props {
  open: boolean
  initialTab?: 'login' | 'signup'
  activeJobTitle?: string | null
  activeJobId?: string | null
  onClose: () => void
  onLogin: (email: string, password: string, activeJobId?: string | null) => Promise<void>
  onSignup: (email: string, password: string, name: string, activeJobId?: string | null) => Promise<void>
}

export function AuthModal({
  open,
  initialTab = 'login',
  activeJobTitle,
  activeJobId,
  onClose,
  onLogin,
  onSignup,
}: Props) {
  const [tab, setTab] = useState<'login' | 'signup'>(initialTab)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [claimActive, setClaimActive] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    const targetJobId = claimActive ? activeJobId : null
    try {
      if (tab === 'login') {
        await onLogin(email, password, targetJobId)
      } else {
        await onSignup(email, password, name, targetJobId)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="auth-header">
          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
              onClick={() => {
                setTab('login')
                setError(null)
              }}
            >
              Log in
            </button>
            <button
              type="button"
              className={`auth-tab ${tab === 'signup' ? 'active' : ''}`}
              onClick={() => {
                setTab('signup')
                setError(null)
              }}
            >
              Sign up
            </button>
          </div>
          <button type="button" className="auth-close" onClick={onClose} aria-label="Close dialog">
            &times;
          </button>
        </div>

        <form className="auth-body" onSubmit={handleSubmit}>
          {error && <div className="auth-error-banner">{error}</div>}

          {tab === 'signup' && (
            <div className="auth-field">
              <label htmlFor="auth-name">Your Name</label>
              <input
                id="auth-name"
                type="text"
                autoComplete="name"
                placeholder="e.g. Alex Smith"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="auth-email">Email Address</label>
            <input
              id="auth-email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              required
              minLength={6}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              placeholder="At least 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {activeJobId && (
            <label className="auth-claim-checkbox">
              <input
                type="checkbox"
                checked={claimActive}
                onChange={(e) => setClaimActive(e.target.checked)}
              />
              <span>
                Save current chat <strong>{activeJobTitle ? `"${activeJobTitle}"` : 'book'}</strong> to this account
              </span>
            </label>
          )}

          <button type="submit" className="auth-submit-btn" disabled={busy}>
            {busy ? 'Please wait...' : tab === 'login' ? 'Log in' : 'Create Account'}
          </button>

          <p className="auth-footer-hint">
            {tab === 'login' ? (
              <>
                Don&apos;t have an account yet?{' '}
                <button
                  type="button"
                  className="link-inline"
                  onClick={() => {
                    setTab('signup')
                    setError(null)
                  }}
                >
                  Sign up
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  className="link-inline"
                  onClick={() => {
                    setTab('login')
                    setError(null)
                  }}
                >
                  Log in
                </button>
              </>
            )}
          </p>
        </form>
      </div>
    </div>
  )
}
