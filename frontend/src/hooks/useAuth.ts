import { useCallback, useEffect, useState } from 'react'
import { api, getAuthToken, setAuthToken } from '../api/client'
import type { User, UserBook } from '../api/types'

export interface AuthState {
  user: User | null
  loading: boolean
  books: UserBook[]
  booksLoading: boolean
  modalOpen: boolean
  modalTab: 'login' | 'signup'
  openLogin: () => void
  openSignup: () => void
  closeModal: () => void
  login: (email: string, password: string, activeJobId?: string | null) => Promise<void>
  signup: (email: string, password: string, name: string, activeJobId?: string | null) => Promise<void>
  logout: () => Promise<void>
  refreshBooks: () => Promise<void>
  claimJob: (jobId: string) => Promise<void>
  deleteBook: (jobId: string) => Promise<void>
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [books, setBooks] = useState<UserBook[]>([])
  const [booksLoading, setBooksLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalTab, setModalTab] = useState<'login' | 'signup'>('login')

  const refreshBooks = useCallback(async () => {
    if (!getAuthToken()) {
      setBooks([])
      return
    }
    setBooksLoading(true)
    try {
      const list = await api.listUserBooks()
      setBooks(list)
    } catch {
      // Ignored if unauthenticated or network error
    } finally {
      setBooksLoading(false)
    }
  }, [])

  // Check saved session on mount
  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      setLoading(false)
      return
    }
    let cancelled = false
    api.getMe()
      .then((res) => {
        if (!cancelled) {
          setUser(res.user)
          void refreshBooks()
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAuthToken(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [refreshBooks])

  const openLogin = useCallback(() => {
    setModalTab('login')
    setModalOpen(true)
  }, [])

  const openSignup = useCallback(() => {
    setModalTab('signup')
    setModalOpen(true)
  }, [])

  const closeModal = useCallback(() => {
    setModalOpen(false)
  }, [])

  const login = useCallback(
    async (email: string, password: string, activeJobId?: string | null) => {
      const res = await api.login(email, password)
      setAuthToken(res.token)
      setUser(res.user)
      setModalOpen(false)
      if (activeJobId) {
        try {
          await api.claimJob(activeJobId)
        } catch {
          // ignore
        }
      }
      void refreshBooks()
    },
    [refreshBooks]
  )

  const signup = useCallback(
    async (email: string, password: string, name: string, activeJobId?: string | null) => {
      const res = await api.signup(email, password, name)
      setAuthToken(res.token)
      setUser(res.user)
      setModalOpen(false)
      if (activeJobId) {
        try {
          await api.claimJob(activeJobId)
        } catch {
          // ignore
        }
      }
      void refreshBooks()
    },
    [refreshBooks]
  )

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // ignore
    }
    setAuthToken(null)
    setUser(null)
    setBooks([])
  }, [])

  const claimJob = useCallback(
    async (jobId: string) => {
      await api.claimJob(jobId)
      void refreshBooks()
    },
    [refreshBooks]
  )

  const deleteBook = useCallback(
    async (jobId: string) => {
      await api.deleteUserBook(jobId)
      void refreshBooks()
    },
    [refreshBooks]
  )

  return {
    user,
    loading,
    books,
    booksLoading,
    modalOpen,
    modalTab,
    openLogin,
    openSignup,
    closeModal,
    login,
    signup,
    logout,
    refreshBooks,
    claimJob,
    deleteBook,
  }
}
