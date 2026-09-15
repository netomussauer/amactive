"""Portas (Protocols) do contexto Cadastros."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from amactive.contexts.cadastros.domain.entities import Cliente, Fornecedor, OrigemCadastroCliente


class ClienteRepository(Protocol):
    async def criar(self, **campos: object) -> Cliente: ...

    async def listar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Cliente], int]: ...

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None: ...

    async def atualizar(self, cliente_id: UUID, **campos: object) -> Cliente | None: ...

    async def inativar(self, cliente_id: UUID) -> bool: ...

    async def upsert_por_email(
        self,
        *,
        email: str,
        nome: str,
        cpf_cnpj: str | None,
        telefone: str | None,
        endereco_logradouro: str | None,
        endereco_cidade: str | None,
        endereco_uf: str | None,
        endereco_cep: str | None,
        cliente_externo_id: str,
        origem_cadastro: OrigemCadastroCliente,
    ) -> Cliente:
        """`INSERT ... ON CONFLICT (email) DO UPDATE` sobre
        `uq_cliente_email_nao_nulo` — ver docs/design-integracao-nuvemshop.md
        §3.3. `origem_cadastro` nunca é sobrescrito num conflito (reflete
        como o registro nasceu); `cliente_externo_id` só é gravado se ainda
        estiver vazio (`COALESCE`); os demais campos são sempre atualizados
        (dados mais recentes do pedido)."""
        ...


class FornecedorRepository(Protocol):
    async def criar(self, **campos: object) -> Fornecedor: ...

    async def listar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Fornecedor], int]: ...

    async def buscar_por_id(self, fornecedor_id: UUID) -> Fornecedor | None: ...

    async def atualizar(self, fornecedor_id: UUID, **campos: object) -> Fornecedor | None: ...

    async def inativar(self, fornecedor_id: UUID) -> bool: ...
