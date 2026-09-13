import { PapelUsuario } from '@/shared/types/api.types'

// Rótulos amigáveis para o enum PapelUsuario — usados na tabela e nos
// formulários (select) da feature de usuários.
export const PAPEL_LABELS: Record<PapelUsuario, string> = {
  [PapelUsuario.ADMIN]: 'Administrador(a)',
  [PapelUsuario.VENDEDOR]: 'Vendedor(a)',
  [PapelUsuario.ESTOQUISTA]: 'Estoquista',
}

export const PAPEL_OPCOES: Array<{ value: PapelUsuario; label: string }> = Object.values(PapelUsuario).map(
  (papel) => ({ value: papel, label: PAPEL_LABELS[papel] }),
)
