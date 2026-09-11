"""Testes unitários de `CriarProdutoCommand`/`AtualizarProdutoCommand`
focados no repasse do `desconto_percentual` — regra de negócio pura, com um
fake em memória para `ProdutoRepository` (sem banco real — ver
tests/integration/test_migration_desconto_promocional.py para o fluxo
completo contra Postgres + API)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from amactive.contexts.catalogo_estoque.application.use_cases.produto_use_cases import (
    AtualizarProdutoCommand,
    CriarProdutoCommand,
)
from amactive.contexts.catalogo_estoque.domain.entities import Produto
from amactive.contexts.catalogo_estoque.domain.exceptions import ProdutoNaoEncontrado

pytestmark = pytest.mark.unit


@dataclass
class _ProdutoRepositoryFake:
    produtos: dict[UUID, Produto] = field(default_factory=dict)

    async def criar(
        self,
        *,
        nome: str,
        descricao: str | None,
        categoria_id: UUID | None,
        marca: str,
        desconto_percentual: Decimal | None = None,
    ) -> Produto:
        produto = Produto(
            id=uuid4(),
            nome=nome,
            descricao=descricao,
            categoria_id=categoria_id,
            marca=marca,
            desconto_percentual=desconto_percentual,
            ativo=True,
            criado_em=datetime.now(UTC),
        )
        self.produtos[produto.id] = produto
        return produto

    async def listar(self, **kwargs: object):  # pragma: no cover - não usado
        raise NotImplementedError

    async def buscar_por_id(self, produto_id: UUID) -> Produto | None:
        return self.produtos.get(produto_id)

    async def atualizar(self, produto_id: UUID, **campos: object) -> Produto | None:
        atual = self.produtos.get(produto_id)
        if atual is None:
            return None
        campos_efetivos = {
            chave: valor
            for chave, valor in campos.items()
            if valor is not None or chave in {"descricao", "categoria_id", "desconto_percentual"}
        }
        # `campos` chega como `**object` (mesma assinatura permissiva do
        # Protocol de produção) — o fake não tem como provar estaticamente
        # que as chaves batem com os campos de `Produto`, mas o teste em si
        # cobre a correção em runtime.
        atualizado = replace(atual, **campos_efetivos)  # type: ignore[arg-type]
        self.produtos[produto_id] = atualizado
        return atualizado

    async def inativar(self, produto_id: UUID) -> bool:  # pragma: no cover - não usado
        raise NotImplementedError


async def test_criar_produto_sem_desconto_persiste_none() -> None:
    repo = _ProdutoRepositoryFake()

    produto = await CriarProdutoCommand(repo).executar(
        nome="Legging Básica", descricao=None, categoria_id=None, marca="AMACTIVE"
    )

    assert produto.desconto_percentual is None


async def test_criar_produto_com_desconto_repassa_o_valor_ao_repositorio() -> None:
    repo = _ProdutoRepositoryFake()

    produto = await CriarProdutoCommand(repo).executar(
        nome="Legging Promocional",
        descricao=None,
        categoria_id=None,
        marca="AMACTIVE",
        desconto_percentual=Decimal("20.00"),
    )

    assert produto.desconto_percentual == Decimal("20.00")
    assert repo.produtos[produto.id].desconto_percentual == Decimal("20.00")


async def test_atualizar_produto_pode_encerrar_promocao_definindo_none() -> None:
    repo = _ProdutoRepositoryFake()
    produto = await CriarProdutoCommand(repo).executar(
        nome="Legging Promocional",
        descricao=None,
        categoria_id=None,
        marca="AMACTIVE",
        desconto_percentual=Decimal("20.00"),
    )

    atualizado = await AtualizarProdutoCommand(repo).executar(
        produto.id,
        nome=produto.nome,
        descricao=None,
        categoria_id=None,
        marca=produto.marca,
        desconto_percentual=None,
        ativo=None,
    )

    assert atualizado.desconto_percentual is None


async def test_atualizar_produto_inexistente_levanta_nao_encontrado() -> None:
    repo = _ProdutoRepositoryFake()

    with pytest.raises(ProdutoNaoEncontrado):
        await AtualizarProdutoCommand(repo).executar(
            uuid4(),
            nome="X",
            descricao=None,
            categoria_id=None,
            marca="AMACTIVE",
            desconto_percentual=None,
            ativo=None,
        )
