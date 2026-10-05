"""Job de expiração das reservas da vitrine: cancela os pedidos PENDENTES cuja
reserva de estoque venceu e devolve as peças à disponibilidade.

Executa uma vez e termina. Em produção roda como CronJob do Kubernetes
(infra/k8s/api/expirar-reservas-cronjob.yaml), a cada 5 minutos. Não depende da
integração com a Nuvemshop, então funciona mesmo com aquele canal em espera.

Uso:
    python -m amactive.scripts.expirar_reservas
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from amactive.contexts.vendas.application.use_cases.expirar_reservas_vencidas import (
    ExpirarReservasVencidasUseCase,
)
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
    SqlAlchemyReservaEstoqueRepository,
)
from amactive.shared_kernel.database import async_session_factory


async def expirar() -> int:
    async with async_session_factory() as session:
        try:
            cancelados = await ExpirarReservasVencidasUseCase(
                SqlAlchemyPedidoRepository(session),
                SqlAlchemyReservaEstoqueRepository(session),
            ).executar(agora=datetime.now(UTC))
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return cancelados


def main() -> None:
    cancelados = asyncio.run(expirar())
    print(f"[expirar-reservas] {cancelados} pedido(s) da vitrine cancelado(s) por reserva vencida.")


if __name__ == "__main__":
    main()
