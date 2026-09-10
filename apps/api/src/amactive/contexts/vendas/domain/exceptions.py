from __future__ import annotations

from amactive.shared_kernel.exceptions import (
    ConflitoDeEstado,
    EntidadeNaoEncontrada,
    ErroDeValidacao,
)


class PedidoNaoEncontrado(EntidadeNaoEncontrada):
    pass


class VarianteDeVendaInvalida(ErroDeValidacao):
    """Variante inexistente ou inativa para venda."""


class PagamentosNaoConferem(ErroDeValidacao):
    """Soma dos pagamentos declarados diverge do valor_total calculado do pedido."""


class PedidoJaCancelado(ConflitoDeEstado):
    pass
