"""Implementação concreta de `PedidoRepository`."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    ProdutoVarianteModel,
)
from amactive.contexts.vendas.domain.entities import (
    FormaPagamento,
    ItemPedido,
    OrigemCanalPedido,
    PagamentoPedido,
    Pedido,
    StatusPedido,
)
from amactive.contexts.vendas.infrastructure.persistence.models import (
    ItemPedidoModel,
    PagamentoPedidoModel,
    PedidoModel,
    ReservaEstoqueModel,
)
from amactive.shared_kernel.pagination import offset_limit

_INDICE_PEDIDO_EXTERNO_UNICO = "uq_pedido_origem_canal_externo"


def _now() -> datetime:
    return datetime.now(UTC)


def violou_unicidade_pedido_externo(exc: IntegrityError) -> bool:
    """Indica se o `IntegrityError` é a violação do índice único parcial
    `uq_pedido_origem_canal_externo` (migrations/000005) — e não outra
    violação de integridade (FK de cliente, `numero` duplicado etc.), que
    nunca deve ser mascarada como "pedido duplicado"."""
    causa = getattr(exc.orig, "__cause__", None)
    nome_constraint = getattr(causa, "constraint_name", None) or getattr(
        exc.orig, "constraint_name", None
    )
    if nome_constraint is not None:
        return bool(nome_constraint == _INDICE_PEDIDO_EXTERNO_UNICO)
    return _INDICE_PEDIDO_EXTERNO_UNICO in str(exc.orig)


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
        usuario_id: UUID | None,
        status: StatusPedido,
        subtotal: Decimal,
        desconto: Decimal,
        valor_total: Decimal,
        observacao: str | None,
        confirmado_em: datetime | None,
        origem_canal: OrigemCanalPedido,
        pedido_externo_id: str | None,
        itens: list[dict],
        pagamentos: list[dict],
        reservado_ate: datetime | None = None,
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
            origem_canal=origem_canal.value,
            pedido_externo_id=pedido_externo_id,
            reservado_ate=reservado_ate,
        )
        self._session.add(pedido_modelo)
        await self._session.flush()

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
            origem_canal=origem_canal,
            pedido_externo_id=pedido_externo_id,
            reservado_ate=reservado_ate,
            itens=itens_entidade,
            pagamentos=pagamentos_entidade,
        )

    async def adicionar_pagamentos(self, pedido_id: UUID, pagamentos: list[dict]) -> None:
        criado_em = _now()
        for pagamento in pagamentos:
            self._session.add(
                PagamentoPedidoModel(
                    id=uuid.uuid4(),
                    pedido_id=pedido_id,
                    forma_pagamento=pagamento["forma_pagamento"].value,
                    valor=pagamento["valor"],
                    criado_em=criado_em,
                )
            )
        await self._session.flush()

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None:
        pedido_modelo = await self._session.get(PedidoModel, pedido_id)
        if pedido_modelo is None:
            return None
        return await self._montar_pedido(pedido_modelo)

    async def existe_pedido_externo(
        self, *, origem_canal: OrigemCanalPedido, pedido_externo_id: str
    ) -> bool:
        encontrado = await self._session.scalar(
            select(PedidoModel.id)
            .where(
                PedidoModel.origem_canal == origem_canal.value,
                PedidoModel.pedido_externo_id == pedido_externo_id,
            )
            .limit(1)
        )
        return encontrado is not None

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        status: StatusPedido | None,
        cliente_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
        origem_canal: OrigemCanalPedido | None = None,
    ) -> tuple[list[Pedido], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        condicoes = []
        if status is not None:
            condicoes.append(PedidoModel.status == status.value)
        if origem_canal is not None:
            condicoes.append(PedidoModel.origem_canal == origem_canal.value)
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
        # Reserva só existe enquanto o pedido está PENDENTE (CHECK do banco).
        if status != StatusPedido.PENDENTE:
            pedido_modelo.reservado_ate = None
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
        origem_canal=OrigemCanalPedido(modelo.origem_canal),
        pedido_externo_id=modelo.pedido_externo_id,
        reservado_ate=modelo.reservado_ate,
        itens=itens,
        pagamentos=pagamentos,
    )


class SqlAlchemyReservaEstoqueRepository:
    """Implementação de `ReservaEstoquePort`. Reserva é um compromisso do
    pedido da vitrine sobre o saldo — nunca altera `estoque.quantidade`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def quantidade_reservada_ativa(self, variante_id: UUID, *, agora: datetime) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(ReservaEstoqueModel.quantidade), 0))
            .join(PedidoModel, PedidoModel.id == ReservaEstoqueModel.pedido_id)
            .where(
                ReservaEstoqueModel.variante_id == variante_id,
                PedidoModel.status == StatusPedido.PENDENTE.value,
                PedidoModel.reservado_ate > agora,
            )
        )
        return int(total or 0)

    async def registrar(self, *, pedido_id: UUID, variante_id: UUID, quantidade: int) -> None:
        self._session.add(
            ReservaEstoqueModel(
                id=uuid.uuid4(),
                pedido_id=pedido_id,
                variante_id=variante_id,
                quantidade=quantidade,
                criado_em=_now(),
            )
        )
        await self._session.flush()

    async def liberar_do_pedido(self, pedido_id: UUID) -> None:
        await self._session.execute(
            delete(ReservaEstoqueModel).where(ReservaEstoqueModel.pedido_id == pedido_id)
        )

    async def pedidos_com_reserva_vencida(self, *, agora: datetime) -> list[UUID]:
        resultado = await self._session.execute(
            select(PedidoModel.id).where(
                PedidoModel.status == StatusPedido.PENDENTE.value,
                PedidoModel.reservado_ate.is_not(None),
                PedidoModel.reservado_ate <= agora,
            )
        )
        return list(resultado.scalars().all())
