from __future__ import annotations

from amactive.shared_kernel.exceptions import (
    ConflitoDeEstado,
    EntidadeNaoEncontrada,
    ErroDeValidacao,
    EstoqueInsuficiente,
)


class CategoriaNaoEncontrada(EntidadeNaoEncontrada):
    pass


class ProdutoNaoEncontrado(EntidadeNaoEncontrada):
    pass


class VarianteNaoEncontrada(EntidadeNaoEncontrada):
    pass


class SkuDuplicado(ConflitoDeEstado):
    pass


class DadosDeMovimentacaoInvalidos(ErroDeValidacao):
    pass


class SaldoDeEstoqueInsuficiente(EstoqueInsuficiente):
    """Tradução do erro do trigger `fn_aplicar_movimentacao_estoque` (SQLSTATE P0001)
    — ver docs/data-model.md § Estratégia de Concorrência — Baixa de Estoque."""
