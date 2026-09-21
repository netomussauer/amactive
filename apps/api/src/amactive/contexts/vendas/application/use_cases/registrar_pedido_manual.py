"""Command: registrar manualmente um pedido de um canal (PDV/WhatsApp/Nuvemshop).

Casca fina sobre `CriarPedidoUseCase` usada pelo `POST /pedidos`: a criação,
a confirmação e a baixa atômica de estoque continuam sendo, byte a byte, as
do `CriarPedidoUseCase` (que também é usado pelo worker de integração
automática, cujo comportamento este módulo NÃO altera). O que este use case
acrescenta é apenas o que só faz sentido no registro manual:

  1. Regra de coerência entre `origem_canal` e `pedido_externo_id` — só a
     NUVEMSHOP tem número de pedido em um sistema externo:
       - NUVEMSHOP -> `pedido_externo_id` obrigatório (número do pedido na loja);
       - PDV       -> NÃO aceita `pedido_externo_id`;
       - WHATSAPP  -> NÃO aceita `pedido_externo_id`: não existe número de pedido
         num sistema externo e, como o índice único vale por (origem, número),
         usar nome/telefone da cliente como "número" geraria um falso conflito
         na segunda compra dela.
  2. Checagem prévia de duplicidade (mesma origem + mesmo número externo),
     ANTES de qualquer escrita — assim uma duplicata nunca chega a baixar
     estoque. A corrida entre duas requisições simultâneas com o mesmo número
     é coberta pelo índice único parcial `uq_pedido_origem_canal_externo`
     (ver o tratamento de `IntegrityError` no router).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido
from amactive.contexts.vendas.domain.exceptions import PedidoExternoDuplicado
from amactive.contexts.vendas.domain.repositories import CatalogoPort, EstoquePort, PedidoRepository
from amactive.shared_kernel.exceptions import ErroDeValidacao


class RegistrarPedidoManualUseCase:
    def __init__(
        self,
        pedido_repository: PedidoRepository,
        catalogo_port: CatalogoPort,
        estoque_port: EstoquePort,
    ) -> None:
        self._pedidos = pedido_repository
        self._criar_pedido = CriarPedidoUseCase(pedido_repository, catalogo_port, estoque_port)

    async def executar(
        self,
        *,
        cliente_id: UUID | None,
        desconto: Decimal,
        observacao: str | None,
        itens: list[ItemPedidoInput],
        pagamentos: list[PagamentoInput],
        usuario_id: UUID,
        origem_canal: OrigemCanalPedido = OrigemCanalPedido.PDV,
        pedido_externo_id: str | None = None,
    ) -> Pedido:
        _validar_origem_e_pedido_externo(origem_canal, pedido_externo_id)

        if pedido_externo_id is not None and await self._pedidos.existe_pedido_externo(
            origem_canal=origem_canal, pedido_externo_id=pedido_externo_id
        ):
            raise PedidoExternoDuplicado(origem_canal.value, pedido_externo_id)

        return await self._criar_pedido.executar(
            cliente_id=cliente_id,
            desconto=desconto,
            observacao=observacao,
            itens=itens,
            pagamentos=pagamentos,
            usuario_id=usuario_id,
            origem_canal=origem_canal,
            pedido_externo_id=pedido_externo_id,
        )


def _validar_origem_e_pedido_externo(
    origem_canal: OrigemCanalPedido, pedido_externo_id: str | None
) -> None:
    if pedido_externo_id is not None and not pedido_externo_id.strip():
        raise ErroDeValidacao("O número do pedido externo não pode ser vazio.")
    if origem_canal != OrigemCanalPedido.NUVEMSHOP and pedido_externo_id is not None:
        raise ErroDeValidacao(
            f"Pedidos de origem {origem_canal.value} não aceitam 'pedido_externo_id' — "
            "ele só é usado em pedidos da NUVEMSHOP (número do pedido na loja). "
            "Remova o campo ou altere a origem para NUVEMSHOP."
        )
    if origem_canal == OrigemCanalPedido.NUVEMSHOP and pedido_externo_id is None:
        raise ErroDeValidacao(
            "Pedidos da NUVEMSHOP exigem o número do pedido na loja ('pedido_externo_id')."
        )
