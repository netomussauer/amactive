import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  UsuarioListResponseSchema,
  UsuarioDetalheResponseSchema,
  type CriarUsuarioDTO,
  type AtualizarUsuarioDTO,
  type RedefinirSenhaDTO,
} from '../schemas/usuario.schema'
import type { UsuarioFilter } from '../types/usuario.types'

// Contexto `identidade`, CRUD administrativo de usuários — ADMIN apenas
// (ver docs/openapi.yaml, tag "Usuários", `x-roles: [ADMIN]`).
export const usuarioService = {
  async list(filter: UsuarioFilter) {
    const raw = await apiClient<unknown>(`/usuarios${buildQueryString(filter)}`)
    return UsuarioListResponseSchema.parse(raw)
  },

  async getById(id: string) {
    const raw = await apiClient<unknown>(`/usuarios/${id}`)
    return UsuarioDetalheResponseSchema.parse(raw)
  },

  async create(payload: CriarUsuarioDTO) {
    const raw = await apiClient<unknown>('/usuarios', { method: 'POST', body: JSON.stringify(payload) })
    return UsuarioDetalheResponseSchema.parse(raw)
  },

  async update(id: string, payload: AtualizarUsuarioDTO) {
    const raw = await apiClient<unknown>(`/usuarios/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
    return UsuarioDetalheResponseSchema.parse(raw)
  },

  // Inativa (soft-delete, ativo=false). Salvaguarda do backend: não permite
  // auto-inativação sendo o único ADMIN ativo (409, ver info.description).
  async inativar(id: string) {
    await apiClient<void>(`/usuarios/${id}`, { method: 'DELETE' })
  },

  // Reset administrativo direto de senha — não é o fluxo de "esqueci minha
  // senha" (sem e-mail, sem senha atual exigida).
  async redefinirSenha(id: string, payload: RedefinirSenhaDTO) {
    await apiClient<void>(`/usuarios/${id}/senha`, { method: 'PATCH', body: JSON.stringify(payload) })
  },
}
