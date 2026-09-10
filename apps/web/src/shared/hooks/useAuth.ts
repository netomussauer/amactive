import { create } from 'zustand'
import { getToken, setToken } from '@/shared/lib/api-client'
import type { Usuario } from '@/shared/types/api.types'

const USER_STORAGE_KEY = 'amactive.user'

function readStoredUser(): Usuario | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as Usuario
  } catch {
    return null
  }
}

type AuthState = {
  user: Usuario | null
  isAuthenticated: boolean
  login: (token: string, user: Usuario) => void
  logout: () => void
}

// Estado de sessão do usuário. O token em si continua sendo a fonte de
// verdade em localStorage (via shared/lib/api-client), este store apenas
// espelha o estado para reatividade de UI (AuthGuard, Sidebar/Header).
export const useAuth = create<AuthState>((set) => ({
  user: readStoredUser(),
  isAuthenticated: Boolean(getToken()),
  login: (token, user) => {
    setToken(token)
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
    set({ user, isAuthenticated: true })
  },
  logout: () => {
    setToken(null)
    localStorage.removeItem(USER_STORAGE_KEY)
    set({ user: null, isAuthenticated: false })
  },
}))
