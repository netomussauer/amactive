// Cliente HTTP centralizado. Toda comunicação com a API passa por aqui —
// nunca use fetch() diretamente em componentes ou hooks de feature.
// Ver docs/frontend-architecture.md §5.1.

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

const TOKEN_STORAGE_KEY = 'amactive.token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
  else localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export class ApiError extends Error {
  constructor(
    public title: string,
    public status: number,
    public detail?: string,
  ) {
    super(title)
    this.name = 'ApiError'
  }
}

export async function apiClient<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (!res.ok) {
    // RFC 7807 Problem Details — ver docs/openapi.yaml components.schemas.ProblemDetails
    const problem = await res.json().catch(() => ({}))

    // Sessão expirada/token inválido em uma chamada autenticada — notifica o
    // AuthGuard (via evento global) para derrubar a sessão e redirecionar ao
    // login. Não dispara para a própria chamada de /auth/login (sem token).
    if (res.status === 401 && token) {
      window.dispatchEvent(new CustomEvent('amactive:unauthorized'))
    }

    throw new ApiError(problem.title ?? 'Erro inesperado', res.status, problem.detail)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
