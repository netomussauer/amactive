"""Casos de uso de gestão administrativa de usuários (CRUD, ADMIN apenas —
ver docs/SDD.md ADR-007 e a matriz RBAC em docs/openapi.yaml).

O hashing de senha acontece aqui (camada de aplicação), reaproveitando
`core/security.hash_senha` — mesmo padrão já usado por
`AutenticarUsuarioUseCase` para `verificar_senha`.
"""

from __future__ import annotations

from uuid import UUID

from amactive.contexts.identidade.domain.entities import PapelUsuario, Usuario
from amactive.contexts.identidade.domain.exceptions import UltimoAdminAtivo, UsuarioNaoEncontrado
from amactive.contexts.identidade.domain.repositories import UsuarioRepository
from amactive.core.security import hash_senha


class CriarUsuarioCommand:
    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    async def executar(self, *, nome: str, email: str, senha: str, papel: PapelUsuario) -> Usuario:
        return await self._repository.criar(
            nome=nome, email=email, senha_hash=hash_senha(senha), papel=papel
        )


class ListarUsuariosQuery:
    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    async def executar(self, *, page: int, per_page: int) -> tuple[list[Usuario], int]:
        return await self._repository.listar(page=page, per_page=per_page)


class ObterUsuarioQuery:
    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    async def executar(self, usuario_id: UUID) -> Usuario:
        usuario = await self._repository.buscar_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNaoEncontrado(f"Usuário {usuario_id} não encontrado.")
        return usuario


class AtualizarUsuarioCommand:
    """Atualiza nome/papel/ativo — nunca a senha (ver `AtualizarSenhaUsuarioCommand`).

    Aplica a salvaguarda do "último ADMIN ativo": um usuário não pode
    desativar a própria conta (`ativo=false`) nem rebaixar o próprio papel
    de ADMIN para outro se ele for o único usuário ADMIN ativo do sistema no
    momento — havendo outro ADMIN ativo, a operação é permitida normalmente.
    """

    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    async def executar(
        self,
        usuario_id: UUID,
        *,
        current_user_id: UUID,
        nome: str,
        papel: PapelUsuario,
        ativo: bool,
    ) -> Usuario:
        usuario_atual = await self._repository.buscar_por_id(usuario_id)
        if usuario_atual is None:
            raise UsuarioNaoEncontrado(f"Usuário {usuario_id} não encontrado.")

        if usuario_id == current_user_id:
            rebaixando_a_si_mesmo = (
                usuario_atual.papel == PapelUsuario.ADMIN and papel != PapelUsuario.ADMIN
            )
            desativando_a_si_mesmo = usuario_atual.ativo and not ativo
            if rebaixando_a_si_mesmo or desativando_a_si_mesmo:
                await self._garantir_que_nao_e_o_unico_admin_ativo()

        usuario = await self._repository.atualizar(usuario_id, nome=nome, papel=papel, ativo=ativo)
        if usuario is None:  # pragma: no cover - defensivo, já checado acima
            raise UsuarioNaoEncontrado(f"Usuário {usuario_id} não encontrado.")
        return usuario

    async def _garantir_que_nao_e_o_unico_admin_ativo(self) -> None:
        total_admins_ativos = await self._repository.contar_admins_ativos()
        if total_admins_ativos <= 1:
            raise UltimoAdminAtivo(
                "Não é possível desativar a própria conta nem rebaixar o "
                "próprio papel: você é o único usuário ADMIN ativo do sistema."
            )


class AtualizarSenhaUsuarioCommand:
    """Reset administrativo direto: o ADMIN define uma nova senha em texto
    plano para o usuário — não é o fluxo de "esqueci minha senha" (sem
    e-mail, fora de escopo)."""

    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    async def executar(self, usuario_id: UUID, *, senha: str) -> None:
        atualizado = await self._repository.atualizar_senha(usuario_id, hash_senha(senha))
        if not atualizado:
            raise UsuarioNaoEncontrado(f"Usuário {usuario_id} não encontrado.")


class InativarUsuarioCommand:
    """Inativa (soft delete, `ativo=false`) — mesmo padrão de
    produtos/variantes/clientes/fornecedores (nunca exclusão física).

    Aplica a mesma salvaguarda do último ADMIN ativo que
    `AtualizarUsuarioCommand` (ver docstring lá) para o caso de
    auto-inativação.
    """

    def __init__(self, repository: UsuarioRepository) -> None:
        self._repository = repository

    async def executar(self, usuario_id: UUID, *, current_user_id: UUID) -> None:
        if usuario_id == current_user_id:
            total_admins_ativos = await self._repository.contar_admins_ativos()
            if total_admins_ativos <= 1:
                raise UltimoAdminAtivo(
                    "Não é possível desativar a própria conta: você é o "
                    "único usuário ADMIN ativo do sistema."
                )

        inativado = await self._repository.inativar(usuario_id)
        if not inativado:
            raise UsuarioNaoEncontrado(f"Usuário {usuario_id} não encontrado.")
