"""Implementação concreta de `PedidoRepository`."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    ProdutoVarianteModel,
)
from amactive.contexts.vendas.domain.entities import (
    FormaPagamento,
    ItemPedido,
    PagamentoPedido,
    Pedido,
    StatusPedido,
)
from amactive.contexts.vendas.infrastructure.persistence.models import (
    ItemPedidoModel,
    PagamentoPedidoModel,
    PedidoModel,
)
from amactive.shared_kernel.pagination import offset_limit


def _now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemyPedidoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def proximo_numero(self) -> str:
        resultado = await self._session.execute(text("SELECT nextval('pedido_numero_seq')"))
        sequencial = resultado.scalar_one()
        return f"PED-{sequencial:06d}"

    async def criar(
        self,
        *,
        numero: str,
        cliente_id: UUID | None,
        usuario_id: UUID,
        status: StatusPedido,
        subtotal: Decimal,
        desconto: Decimal,
        valor_total: Decimal,
        observacao: str | None,
        confirmado_em: datetime | None,
        itens: list[dict],
        pagamentos: list[dict],
    ) -> Pedido:
        pedido_id = uuid.uuid4()
        criado_em = _now()

        pedido_modelo = PedidoModel(
            id=pedido_id,
            numero=numero,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            status=status.value,
            subtotal=subtotal,
            desconto=desconto,
            valor_total=valor_total,
            observacao=observacao,
            criado_em=criado_em,
            confirmado_em=confirmado_em,
            cancelado_em=None,
        )
        self._session.add(pedido_modelo)

        itens_entidade: list[ItemPedido] = []
        for item in itens:
            item_id = uuid.uuid4()
            self._session.add(
                ItemPedidoModel(
                    id=item_id,
                    pedido_id=pedido_id,
                    variante_id=item["variante_id"],
                    quantidade=item["quantidade"],
                    preco_unitario=item["preco_unitario"],
                    desconto_item=item["desconto_item"],
                    subtotal=item["subtotal"],
                )
            )
            itens_entidade.append(
                ItemPedido(
                    id=item_id,
                    variante_id=item["variante_id"],
                    sku=item["sku"],
                    quantidade=item["quantidade"],
                    preco_unitario=item["preco_unitario"],
                    desconto_item=item["desconto_item"],
                    subtotal=item["subtotal"],
                )
            )

        pagamentos_entidade: list[PagamentoPedido] = []
        for pagamento in pagamentos:
            pagamento_id = uuid.uuid4()
            self._session.add(
                PagamentoPedidoModel(
                    id=pagamento_id,
                    pedido_id=pedido_id,
                    forma_pagamento=pagamento["forma_pagamento"].value,
                    valor=pagamento["valor"],
                    criado_em=criado_em,
                )
            )
            pagamentos_entidade.append(
                PagamentoPedido(
                    id=pagamento_id,
                    forma_pagamento=pagamento["forma_pagamento"],
                    valor=pagamento["valor"],
                )
            )

        await self._session.flush()

        return Pedido(
            id=pedido_id,
            numero=numero,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            status=status,
            subtotal=subtotal,
            desconto=desconto,
            valor_total=valor_total,
            observacao=observacao,
            criado_em=criado_em,
            confirmado_em=confirmado_em,
            cancelado_em=None,
            itens=itens_entidade,
            pagamentos=pagamentos_entidade,
        )

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None:
        pedido_modelo = await self._session.get(PedidoModel, pedido_id)
        if pedido_modelo is None:
            return None
        return await self._montar_pedido(pedido_modelo)

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        status: StatusPedido | None,
        cliente_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> tuple[list[Pedido], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        condicoes = []
        if status is not None:
            condicoes.append(PedidoModel.status == status.value)
        if cliente_id is not None:
            condicoes.append(PedidoModel.cliente_id == cliente_id)
        if data_inicio is not None:
            condicoes.append(
                PedidoModel.criado_em >= datetime.combine(data_inicio, time.min, tzinfo=UTC)
            )
        if data_fim is not None:
            condicoes.append(
                PedidoModel.criado_em <= datetime.combine(data_fim, time.max, tzinfo=UTC)
            )

        total = await self._session.scalar(
            select(func.count()).select_from(PedidoModel).where(*condicoes)
        )
        resultado = await self._session.execute(
            select(PedidoModel)
            .where(*condicoes)
            .order_by(PedidoModel.criado_em.desc())
            .offset(offset)
            .limit(limit)
        )
        pedidos = [
            _pedido_para_entidade(m, itens=[], pagamentos=[]) for m in resultado.scalars().all()
        ]
        return pedidos, int(total or 0)

    async def atualizar_status(
        self, pedido_id: UUID, *, status: StatusPedido, timestamp: datetime
    ) -> None:
        pedido_modelo = await self._session.get(PedidoModel, pedido_id)
        if pedido_modelo is None:
            return
        pedido_modelo.status = status.value
        if status == StatusPedido.CANCELADO:
            pedido_modelo.cancelado_em = timestamp
        elif status == StatusPedido.CONFIRMADO:
            pedido_modelo.confirmado_em = timestamp
        await self._session.flush()

    async def _montar_pedido(self, pedido_modelo: PedidoModel) -> Pedido:
        itens_resultado = await self._session.execute(
            select(ItemPedidoModel, ProdutoVarianteModel.sku)
            .join(ProdutoVarianteModel, ProdutoVarianteModel.id == ItemPedidoModel.variante_id)
            .where(ItemPedidoModel.pedido_id == pedido_modelo.id)
        )
        itens = [
            ItemPedido(
                id=item.id,
                variante_id=item.variante_id,
                sku=sku,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                desconto_item=item.desconto_item,
                subtotal=item.subtotal,
            )
            for item, sku in itens_resultado.all()
        ]

        pagamentos_resultado = await self._session.execute(
            select(PagamentoPedidoModel).where(PagamentoPedidoModel.pedido_id == pedido_modelo.id)
        )
        pagamentos = [
            PagamentoPedido(
                id=p.id, forma_pagamento=FormaPagamento(p.forma_pagamento), valor=p.valor
            )
            for p in pagamentos_resultado.scalars().all()
        ]

        return _pedido_para_entidade(pedido_modelo, itens=itens, pagamentos=pagamentos)


def _pedido_para_entidade(
    modelo: PedidoModel, *, itens: list[ItemPedido], pagamentos: list[PagamentoPedido]
) -> Pedido:
    return Pedido(
        id=modelo.id,
        numero=modelo.numero,
        cliente_id=modelo.cliente_id,
        usuario_id=modelo.usuario_id,
        status=StatusPedido(modelo.status),
        subtotal=modelo.subtotal,
        desconto=modelo.desconto,
        valor_total=modelo.valor_total,
        observacao=modelo.observacao,
        criado_em=modelo.criado_em,
        confirmado_em=modelo.confirmado_em,
        cancelado_em=modelo.cancelado_em,
        itens=itens,
        pagamentos=pagamentos,
    )
