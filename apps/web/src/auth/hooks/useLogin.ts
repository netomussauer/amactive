import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api-client'
import { useAuth } from '@/shared/hooks/useAuth'
import { LoginResponseSchema, type LoginFormValues } from '../schemas/auth.schema'

export function useLogin() {
  const login = useAuth((state) => state.login)

  return useMutation({
    mutationFn: async (values: LoginFormValues) => {
      const raw = await apiClient<unknown>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(values),
      })
      return LoginResponseSchema.parse(raw)
    },
    onSuccess: (data) => {
      login(data.access_token, data.usuario)
    },
  })
}
