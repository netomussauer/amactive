"""Command: a equipe confirma o pagamento de um pedido da vitrine.

Único ponto em que um pedido da vitrine vira venda de fato: a reserva é
removida e a baixa real de estoque é registrada (`registrar_saida_venda`, via
`movimentacao_estoque`), tudo na mesma transação. Regras:

  1. Só pedido PENDENTE da origem VITRINE pode ser confirmado.
  2. Reserva vencida bloqueia a confirmação (`ReservaVencida`): nesse caso as
     unidades podem já ter sido prometidas a outro cliente — a equipe cancela
     e pede novo checkout, em vez de forçar uma baixa sem reserva.
  3. A soma dos pagamentos precisa bater com `valor_total` (mesma regra do PDV).
  4. As linhas de `estoque` são travadas (FOR UPDATE) em ordem por `variante_id`
     antes da baixa, para serializar com checkouts concorrentes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from amactive.contexts.vendas.application.dto import PagamentoInput
from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido, StatusPedido
from amactive.contexts.vendas.domain.exceptions import (
    PagamentosNaoConferem,
    PedidoNaoAguardandoPagamento,
    PedidoNaoEncontrado,
    ReservaVencida,
)
from amactive.contexts.vendas.domain.repositories import (
    EstoquePort,
    PedidoRepository,
    ReservaEstoquePort,
)


class ConfirmarPagamentoVitrineUseCase:
    def __init__(
        self,
        pedido_repository: PedidoRepository,
        estoque_port: EstoquePort,
        reserva_port: ReservaEstoquePort,
    ) -> None:
        self._pedidos = pedido_repository
        self._estoque = estoque_port
        self._reservas = reserva_port

    async def executar(
        self,
        pedido_id: UUID,
        *,
        pagamentos: list[PagamentoInput],
        usuario_id: UUID,
        agora: datetime,
    ) -> Pedido:
        pedido = await self._pedidos.buscar_por_id(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontrado(f"Pedido {pedido_id} não encontrado.")
        if (
            pedido.origem_canal != OrigemCanalPedido.VITRINE
            or pedido.status != StatusPedido.PENDENTE
        ):
            raise PedidoNaoAguardandoPagamento(
                f"O pedido {pedido.numero} não está aguardando pagamento da vitrine."
            )
        if pedido.reservado_ate is None or pedido.reservado_ate <= agora:
            raise ReservaVencida(
                f"A reserva do pedido {pedido.numero} venceu. Cancele o pedido e peça um novo "
                "checkout para reservar as peças novamente."
            )

        soma_pagamentos = sum((p.valor for p in pagamentos), Decimal("0.00"))
        if soma_pagamentos != pedido.valor_total:
            raise PagamentosNaoConferem(
                f"Soma dos pagamentos ({soma_pagamentos}) difere do valor total do "
                f"pedido ({pedido.valor_total})."
            )

        itens_ordenados = sorted(pedido.itens, key=lambda i: str(i.variante_id))
        for item in itens_ordenados:
            await self._estoque.saldo_bloqueado(item.variante_id)

        await self._reservas.liberar_do_pedido(pedido.id)
        for item in itens_ordenados:
            await self._estoque.registrar_saida_venda(
                variante_id=item.variante_id,
                quantidade=item.quantidade,
                pedido_id=pedido.id,
                usuario_id=usuario_id,
            )

        await self._pedidos.adicionar_pagamentos(
            pedido.id,
            [{"forma_pagamento": p.forma_pagamento, "valor": p.valor} for p in pagamentos],
        )
        await self._pedidos.atualizar_status(
            pedido.id, status=StatusPedido.CONFIRMADO, timestamp=agora
        )

        confirmado = await self._pedidos.buscar_por_id(pedido.id)
        assert confirmado is not None  # acabamos de validar a existência
        return confirmado
