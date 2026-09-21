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


class PedidoExternoDuplicado(ConflitoDeEstado):
    """Já existe um pedido registrado com o mesmo número externo para a mesma
    origem (canal) — ver `uq_pedido_origem_canal_externo` (migrations/000005).

    Específica do registro MANUAL de pedidos (`POST /pedidos`); o caminho de
    integração automática traduz a mesma violação de unicidade por conta
    própria (idempotência do webhook), sem passar por esta exceção.
    """

    def __init__(self, origem_canal: str, pedido_externo_id: str) -> None:
        super().__init__(
            f"Já existe um pedido {origem_canal} com o número '{pedido_externo_id}'. "
            "Confira o número informado — o mesmo pedido não pode ser registrado duas vezes."
        )
        self.origem_canal = origem_canal
        self.pedido_externo_id = pedido_externo_id
