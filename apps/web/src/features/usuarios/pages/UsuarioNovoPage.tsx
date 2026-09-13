import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card } from '@/shared/components/ui/Card'
import { routes } from '@/shared/lib/routes'
import { UsuarioForm } from '../components/UsuarioForm'

export function UsuarioNovoPage() {
  const navigate = useNavigate()

  return (
    <PageWrapper title="Novo usuário" description="Cadastre um novo usuário com acesso ao sistema AMACTIVE.">
      <Card className="max-w-2xl">
        <UsuarioForm onSuccess={(usuario) => navigate(routes.usuarioDetalhe(usuario.id))} />
      </Card>
    </PageWrapper>
  )
}
