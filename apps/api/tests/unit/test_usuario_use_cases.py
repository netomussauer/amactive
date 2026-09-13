"""Testes unitários dos casos de uso de gestão administrativa de usuários
(CRUD, ADMIN apenas) — foco na salvaguarda do "último ADMIN ativo" e na
detecção de e-mail duplicado, com um fake em memória para
`UsuarioRepository` (sem banco real — ver
tests/integration/test_usuarios_crud.py para o fluxo completo via HTTP)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from amactive.contexts.identidade.application.use_cases.usuario_use_cases import (
    AtualizarSenhaUsuarioCommand,
    AtualizarUsuarioCommand,
    CriarUsuarioCommand,
    InativarUsuarioCommand,
    ObterUsuarioQuery,
)
from amactive.contexts.identidade.domain.entities import PapelUsuario, Usuario
from amactive.contexts.identidade.domain.exceptions import (
    EmailDuplicado,
    UltimoAdminAtivo,
    UsuarioNaoEncontrado,
)
from amactive.core.security import verificar_senha

pytestmark = pytest.mark.unit


@dataclass
class _UsuarioRepositoryFake:
    usuarios: dict[UUID, Usuario] = field(default_factory=dict)

    async def buscar_por_email(self, email: str) -> Usuario | None:
        return next((u for u in self.usuarios.values() if u.email == email), None)

    async def criar(
        self, *, nome: str, email: str, senha_hash: str, papel: PapelUsuario
    ) -> Usuario:
        if await self.buscar_por_email(email) is not None:
            raise EmailDuplicado(f"O e-mail '{email}' já está em uso por outro usuário.")
        usuario = Usuario(
            id=uuid4(),
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            papel=papel,
            ativo=True,
            criado_em=datetime.now(UTC),
        )
        self.usuarios[usuario.id] = usuario
        return usuario

    async def listar(self, **kwargs: object) -> tuple[list[Usuario], int]:  # pragma: no cover
        raise NotImplementedError

    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        return self.usuarios.get(usuario_id)

    async def atualizar(
        self, usuario_id: UUID, *, nome: str, papel: PapelUsuario, ativo: bool
    ) -> Usuario | None:
        atual = self.usuarios.get(usuario_id)
        if atual is None:
            return None
        atualizado = replace(atual, nome=nome, papel=papel, ativo=ativo)
        self.usuarios[usuario_id] = atualizado
        return atualizado

    async def atualizar_senha(self, usuario_id: UUID, senha_hash: str) -> bool:
        atual = self.usuarios.get(usuario_id)
        if atual is None:
            return False
        self.usuarios[usuario_id] = replace(atual, senha_hash=senha_hash)
        return True

    async def inativar(self, usuario_id: UUID) -> bool:
        atual = self.usuarios.get(usuario_id)
        if atual is None:
            return False
        self.usuarios[usuario_id] = replace(atual, ativo=False)
        return True

    async def contar_admins_ativos(self) -> int:
        return sum(1 for u in self.usuarios.values() if u.papel == PapelUsuario.ADMIN and u.ativo)


def _usuario(
    *, papel: PapelUsuario = PapelUsuario.ADMIN, ativo: bool = True, email: str | None = None
) -> Usuario:
    identificador = uuid4()
    return Usuario(
        id=identificador,
        nome="Usuário Teste",
        email=email or f"user-{identificador.hex[:8]}@amactive.dev",
        senha_hash="hash-preexistente",
        papel=papel,
        ativo=ativo,
        criado_em=datetime.now(UTC),
    )


# ── CriarUsuarioCommand ──
async def test_criar_usuario_faz_hash_da_senha_e_nunca_a_expoe_em_texto_plano() -> None:
    repo = _UsuarioRepositoryFake()

    usuario = await CriarUsuarioCommand(repo).executar(
        nome="Ana Vendedora",
        email="ana@amactive.dev",
        senha="senha-super-secreta",
        papel=PapelUsuario.VENDEDOR,
    )

    assert usuario.senha_hash != "senha-super-secreta"
    assert verificar_senha("senha-super-secreta", usuario.senha_hash)


async def test_criar_usuario_com_email_duplicado_levanta_email_duplicado() -> None:
    repo = _UsuarioRepositoryFake()
    await CriarUsuarioCommand(repo).executar(
        nome="Ana", email="duplicado@amactive.dev", senha="senha12345", papel=PapelUsuario.VENDEDOR
    )

    with pytest.raises(EmailDuplicado):
        await CriarUsuarioCommand(repo).executar(
            nome="Outra Ana",
            email="duplicado@amactive.dev",
            senha="outrasenha123",
            papel=PapelUsuario.ESTOQUISTA,
        )


# ── ObterUsuarioQuery ──
async def test_obter_usuario_inexistente_levanta_usuario_nao_encontrado() -> None:
    repo = _UsuarioRepositoryFake()

    with pytest.raises(UsuarioNaoEncontrado):
        await ObterUsuarioQuery(repo).executar(uuid4())


# ── AtualizarUsuarioCommand — salvaguarda do último ADMIN ativo ──
async def test_atualizar_usuario_inexistente_levanta_usuario_nao_encontrado() -> None:
    repo = _UsuarioRepositoryFake()

    with pytest.raises(UsuarioNaoEncontrado):
        await AtualizarUsuarioCommand(repo).executar(
            uuid4(),
            current_user_id=uuid4(),
            nome="X",
            papel=PapelUsuario.VENDEDOR,
            ativo=True,
        )


async def test_ultimo_admin_nao_pode_se_autodesativar() -> None:
    repo = _UsuarioRepositoryFake()
    admin = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    repo.usuarios[admin.id] = admin

    with pytest.raises(UltimoAdminAtivo):
        await AtualizarUsuarioCommand(repo).executar(
            admin.id,
            current_user_id=admin.id,
            nome=admin.nome,
            papel=PapelUsuario.ADMIN,
            ativo=False,
        )


async def test_ultimo_admin_nao_pode_rebaixar_o_proprio_papel() -> None:
    repo = _UsuarioRepositoryFake()
    admin = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    repo.usuarios[admin.id] = admin

    with pytest.raises(UltimoAdminAtivo):
        await AtualizarUsuarioCommand(repo).executar(
            admin.id,
            current_user_id=admin.id,
            nome=admin.nome,
            papel=PapelUsuario.VENDEDOR,
            ativo=True,
        )


async def test_admin_pode_se_autodesativar_quando_ha_outro_admin_ativo() -> None:
    repo = _UsuarioRepositoryFake()
    admin_1 = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    admin_2 = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    repo.usuarios[admin_1.id] = admin_1
    repo.usuarios[admin_2.id] = admin_2

    atualizado = await AtualizarUsuarioCommand(repo).executar(
        admin_1.id,
        current_user_id=admin_1.id,
        nome=admin_1.nome,
        papel=PapelUsuario.ADMIN,
        ativo=False,
    )

    assert atualizado.ativo is False


async def test_admin_pode_rebaixar_o_proprio_papel_quando_ha_outro_admin_ativo() -> None:
    repo = _UsuarioRepositoryFake()
    admin_1 = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    admin_2 = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    repo.usuarios[admin_1.id] = admin_1
    repo.usuarios[admin_2.id] = admin_2

    atualizado = await AtualizarUsuarioCommand(repo).executar(
        admin_1.id,
        current_user_id=admin_1.id,
        nome=admin_1.nome,
        papel=PapelUsuario.VENDEDOR,
        ativo=True,
    )

    assert atualizado.papel == PapelUsuario.VENDEDOR


async def test_admin_pode_desativar_outro_usuario_sem_acionar_a_salvaguarda() -> None:
    repo = _UsuarioRepositoryFake()
    admin = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    vendedor = _usuario(papel=PapelUsuario.VENDEDOR, ativo=True)
    repo.usuarios[admin.id] = admin
    repo.usuarios[vendedor.id] = vendedor

    atualizado = await AtualizarUsuarioCommand(repo).executar(
        vendedor.id,
        current_user_id=admin.id,
        nome=vendedor.nome,
        papel=PapelUsuario.VENDEDOR,
        ativo=False,
    )

    assert atualizado.ativo is False


# ── InativarUsuarioCommand — mesma salvaguarda para o soft delete ──
async def test_ultimo_admin_nao_pode_se_autoinativar() -> None:
    repo = _UsuarioRepositoryFake()
    admin = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    repo.usuarios[admin.id] = admin

    with pytest.raises(UltimoAdminAtivo):
        await InativarUsuarioCommand(repo).executar(admin.id, current_user_id=admin.id)

    assert repo.usuarios[admin.id].ativo is True


async def test_admin_pode_se_autoinativar_quando_ha_outro_admin_ativo() -> None:
    repo = _UsuarioRepositoryFake()
    admin_1 = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    admin_2 = _usuario(papel=PapelUsuario.ADMIN, ativo=True)
    repo.usuarios[admin_1.id] = admin_1
    repo.usuarios[admin_2.id] = admin_2

    await InativarUsuarioCommand(repo).executar(admin_1.id, current_user_id=admin_1.id)

    assert repo.usuarios[admin_1.id].ativo is False


async def test_inativar_usuario_inexistente_levanta_usuario_nao_encontrado() -> None:
    repo = _UsuarioRepositoryFake()

    with pytest.raises(UsuarioNaoEncontrado):
        await InativarUsuarioCommand(repo).executar(uuid4(), current_user_id=uuid4())


# ── AtualizarSenhaUsuarioCommand ──
async def test_atualizar_senha_faz_hash_e_nunca_expoe_a_senha_em_texto_plano() -> None:
    repo = _UsuarioRepositoryFake()
    usuario = _usuario()
    repo.usuarios[usuario.id] = usuario

    await AtualizarSenhaUsuarioCommand(repo).executar(usuario.id, senha="nova-senha-123")

    novo_hash = repo.usuarios[usuario.id].senha_hash
    assert novo_hash != "nova-senha-123"
    assert verificar_senha("nova-senha-123", novo_hash)


async def test_atualizar_senha_usuario_inexistente_levanta_usuario_nao_encontrado() -> None:
    repo = _UsuarioRepositoryFake()

    with pytest.raises(UsuarioNaoEncontrado):
        await AtualizarSenhaUsuarioCommand(repo).executar(uuid4(), senha="nova-senha-123")
