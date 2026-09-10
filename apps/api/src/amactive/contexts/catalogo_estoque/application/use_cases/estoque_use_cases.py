"""Casos de uso de Estoque e Movimentação (Command/Query)."""

from __future__ import annotations

from dataclasses import replace
from typing import ClassVar
from uuid import UUID

from amactive.contexts.catalogo_estoque.domain.entities import (
    Estoque,
    MotivoMovimentacao,
    MovimentacaoEstoque,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.domain.exceptions import (
    DadosDeMovimentacaoInvalidos,
    VarianteNaoEncontrada,
)
from amactive.contexts.catalogo_estoque.domain.repositories import (
    EstoqueRepository,
    MovimentacaoRepository,
    VarianteRepository,
)


class ListarEstoqueQuery:
    def __init__(self, repository: EstoqueRepository) -> None:
        self._repository = repository

    async def executar(
        self, *, page: int, per_page: int, sku: str | None
    ) -> tuple[list[Estoque], int]:
        return await self._repository.listar(page=page, per_page=per_page, sku=sku)


class ListarAlertasEstoqueQuery:
    def __init__(self, repository: EstoqueRepository) -> None:
        self._repository = repository

    async def executar(self) -> list[Estoque]:
        return await self._repository.listar_em_alerta()


class ListarMovimentacoesQuery:
    def __init__(self, repository: MovimentacaoRepository) -> None:
        self._repository = repository

    async def executar(
        self,
        *,
        page: int,
        per_page: int,
        variante_id: UUID | None,
        tipo: TipoMovimentacao | None,
    ) -> tuple[list[MovimentacaoEstoque], int]:
        return await self._repository.listar(
            page=page, per_page=per_page, variante_id=variante_id, tipo=tipo
        )


class CriarMovimentacaoCommand:
    """Registra movimentações MANUAIS (compra, ajuste de inventário, devolução,
    perda). Movimentações de motivo VENDA são geradas exclusivamente pelo
    contexto de Vendas ao confirmar um Pedido, nunca por este caso de uso —
    ver docs/openapi.yaml `POST /estoque/movimentacoes`.

    A regra de ouro (nunca fazer UPDATE direto em `estoque`) é cumprida pelo
    `MovimentacaoRepository`: ele sempre faz `INSERT INTO movimentacao_estoque`
    e delega a atualização atômica do saldo ao trigger de banco (ver
    docs/data-model.md § Estratégia de Concorrência — Baixa de Estoque).
    """

    _MOTIVOS_PERMITIDOS: ClassVar[set[MotivoMovimentacao]] = {
        MotivoMovimentacao.COMPRA,
        MotivoMovimentacao.AJUSTE_INVENTARIO,
        MotivoMovimentacao.DEVOLUCAO,
        MotivoMovimentacao.PERDA,
    }

    def __init__(
        self,
        variante_repository: VarianteRepository,
        movimentacao_repository: MovimentacaoRepository,
    ) -> None:
        self._variantes = variante_repository
        self._movimentacoes = movimentacao_repository

    async def executar(
        self,
        *,
        variante_id: UUID,
        tipo: TipoMovimentacao,
        quantidade: int,
        motivo: MotivoMovimentacao,
        fornecedor_id: UUID | None,
        usuario_id: UUID,
    ) -> MovimentacaoEstoque:
        if motivo not in self._MOTIVOS_PERMITIDOS:
            raise DadosDeMovimentacaoInvalidos(
                f"Motivo '{motivo.value}' não é permitido para registro manual de "
                "movimentação (use o fluxo de Vendas para motivo=VENDA)."
            )
        variante = await self._variantes.buscar_por_id(variante_id)
        if variante is None:
            raise VarianteNaoEncontrada(f"Variante {variante_id} não encontrada.")

        movimentacao = await self._movimentacoes.registrar(
            variante_id=variante_id,
            tipo=tipo,
            quantidade=quantidade,
            motivo=motivo,
            usuario_id=usuario_id,
            fornecedor_id=fornecedor_id,
        )
        return replace(movimentacao, sku=variante.sku)
