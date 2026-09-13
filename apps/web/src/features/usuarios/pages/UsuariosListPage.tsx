import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button } from '@/shared/components/ui/Button'
import { Pagination } from '@/shared/components/ui/Pagination'
import { routes } from '@/shared/lib/routes'
import { UsuarioTable } from '../components/UsuarioTable'
import { useUsuarios } from '../hooks/useUsuarios'

export function UsuariosListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useUsuarios({ page, per_page: 20 })

  return (
    <PageWrapper
      title="Usuários"
      description="Gestão de usuários com acesso ao sistema AMACTIVE."
      actions={
        <Button onClick={() => navigate(routes.usuarioNovo)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Novo usuário
        </Button>
      }
    >
      <UsuarioTable usuarios={data?.data ?? []} isLoading={isLoading} />

      {data && <Pagination pagination={data.pagination} onPageChange={setPage} />}
    </PageWrapper>
  )
}
