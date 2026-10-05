"""Command: cancela os pedidos da vitrine cuja reserva de estoque venceu.

Um pedido PENDENTE segura as unidades que pediu só até `reservado_ate`. Depois
disso, o pedido é cancelado e a reserva removida, devolvendo as peças à
disponibilidade. Este caso de uso roda de duas formas:

  - periodicamente, pelo CronJob `expirar-reservas` (ver
    apps/api/src/amactive/scripts/expirar_reservas.py), que é a forma normal;
  - de forma preguiçosa, no início de cada checkout da vitrine, para o caso de
    o job estar atrasado. A disponibilidade já ignora reservas vencidas, então
    a expiração atrasada não superestima estoque, só deixa o pedido "PENDENTE"
    na lista administrativa por mais tempo.

Idempotente: rodar de novo sem nada vencido não faz nada.
"""

from __future__ import annotations

from datetime import datetime

from amactive.contexts.vendas.domain.entities import StatusPedido
from amactive.contexts.vendas.domain.repositories import PedidoRepository, ReservaEstoquePort


class ExpirarReservasVencidasUseCase:
    def __init__(
        self, pedido_repository: PedidoRepository, reserva_port: ReservaEstoquePort
    ) -> None:
        self._pedidos = pedido_repository
        self._reservas = reserva_port

    async def executar(self, *, agora: datetime) -> int:
        """Retorna quantos pedidos foram cancelados por expiração."""
        vencidos = await self._reservas.pedidos_com_reserva_vencida(agora=agora)
        for pedido_id in vencidos:
            await self._reservas.liberar_do_pedido(pedido_id)
            await self._pedidos.atualizar_status(
                pedido_id, status=StatusPedido.CANCELADO, timestamp=agora
            )
        return len(vencidos)
