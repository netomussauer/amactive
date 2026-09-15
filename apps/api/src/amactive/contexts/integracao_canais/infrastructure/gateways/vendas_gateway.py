"""Implementa `PedidoIntegracaoPort` (`domain/repositories.py`) chamando
`CriarPedidoUseCase` in-process — ver docs/design-integracao-nuvemshop.md
§3.1/§3.4.

Reaproveita, byte a byte, o mesmo padrão de injeção de dependência já usado
por `vendas/infrastructure/api/router.py` (`POST /pedidos`): uma
`SqlAlchemyPedidoRepository` + `CatalogoEstoqueGateway` (que atua como
`CatalogoPort` e `EstoquePort` ao mesmo tempo) instanciados sobre a MESMA
`AsyncSession` recebida no construtor deste gateway — é isso que garante a
atomicidade Pedido+Estoque também para pedidos originados por webhook, sem
nenhuma linha nova em `CriarPedidoUseCase`.

`pagamentos`/`itens` chegam prontos (já montados pelo chamador —
`ProcessarWebhookPedidoUseCase`, design §5.3 passo 4: um único
`PagamentoInput(forma_pagamento=NUVEMSHOP, valor=valor_total)`) porque é
exatamente essa a assinatura publicada por `PedidoIntegracaoPort`
(`domain/repositories.py`, fonte da verdade) — este gateway não decide
regra de negócio nenhuma sobre pagamento, só encaixa o `usuario_id` do
usuário de sistema e delega para `CriarPedidoUseCase`.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.infrastructure.persistence.repositories import (
    SqlAlchemyUsuarioRepository,
)
from amactive.contexts.integracao_canais.domain.exceptions import (
    PedidoExternoJaProcessado,
    UsuarioIntegracaoNaoEncontrado,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido
from amactive.contexts.vendas.infrastructure.persistence.gateways import CatalogoEstoqueGateway
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
)

# E-mail bem-conhecido do usuário de sistema que "assina" pedidos importados
# — mesmo valor de `scripts/bootstrap_usuario_integracao.py`
# (`EMAIL_USUARIO_INTEGRACAO`), duplicado aqui deliberadamente (não
# importado do módulo de script) para não acoplar este gateway de produção a
# um módulo de `scripts/`, que é código operacional, não uma dependência de
# runtime da aplicação.
EMAIL_USUARIO_INTEGRACAO = "integracao.nuvemshop@sistema.amactive.internal"

# Cache de processo do `usuario_id` resolvido por e-mail (design §3.1: "o
# worker resolve o id desse usuário uma vez, por e-mail bem-conhecido, no
# startup, e mantém em cache de processo — evita hardcodar um UUID que
# mudaria entre ambientes"). Deliberadamente populado no primeiro uso (não
# no import deste módulo, que roda antes de qualquer conexão de banco
# existir) — um `dict` mutável em vez de uma variável `UUID | None` simples
# só para expor `resetar_cache_usuario_integracao_para_testes` sem precisar
# de `global` dentro do método.
_cache_usuario_integracao: dict[str, UUID] = {}


def resetar_cache_usuario_integracao_para_testes() -> None:
    """Uso exclusivo de testes de integração — limpa o cache de processo do
    `usuario_id` de integração entre execuções isoladas.

    Cada teste de integração roda em uma transação própria, revertida no
    teardown (ver `tests/integration/conftest.py`); sem este reset, um
    `usuario_id` cacheado por um teste anterior — cuja linha já foi
    desfeita pelo rollback — provocaria violação de FK (`pedido.usuario_id`)
    em testes seguintes que resolvem o mesmo e-mail a partir de uma
    transação nova. Nunca chamada pela aplicação em produção, onde o cache
    de processo é exatamente o comportamento desejado (design §3.1)."""
    _cache_usuario_integracao.clear()


class VendasIntegracaoGateway:
    """Implementa `PedidoIntegracaoPort` — ver docstring do módulo."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def confirmar_pedido_externo(
        self,
        *,
        cliente_id: UUID,
        itens: list[ItemPedidoInput],
        pagamentos: list[PagamentoInput],
        origem_canal: OrigemCanalPedido,
        pedido_externo_id: str,
    ) -> Pedido:
        usuario_id = await self._resolver_usuario_integracao_id()
        pedido_repository = SqlAlchemyPedidoRepository(self._session)
        catalogo_estoque_gateway = CatalogoEstoqueGateway(self._session)
        use_case = CriarPedidoUseCase(
            pedido_repository, catalogo_estoque_gateway, catalogo_estoque_gateway
        )

        try:
            return await use_case.executar(
                cliente_id=cliente_id,
                # Um pedido Nuvemshop chega já pago via checkout do canal,
                # sem desconto adicional aplicado pelo AMACTIVE — o valor
                # total já reflete qualquer desconto que a Nuvemshop tenha
                # concedido no ato da compra (design §3.1).
                desconto=Decimal("0.00"),
                observacao=None,
                itens=itens,
                pagamentos=pagamentos,
                usuario_id=usuario_id,
                origem_canal=origem_canal,
                pedido_externo_id=pedido_externo_id,
            )
        except IntegrityError as exc:
            # `UNIQUE (origem_canal, pedido_externo_id) WHERE
            # pedido_externo_id IS NOT NULL` violada — defesa em
            # profundidade contra duplicidade de pedido externo (design
            # §3.1). Traduzida para uma exceção de domínio de
            # `integracao_canais`, tratada como sucesso idempotente por
            # quem chama (`ProcessarWebhookPedidoUseCase`), não como erro.
            await self._session.rollback()
            raise PedidoExternoJaProcessado(
                f"Pedido externo '{pedido_externo_id}' (origem {origem_canal.value}) já "
                "foi processado anteriormente."
            ) from exc

    async def _resolver_usuario_integracao_id(self) -> UUID:
        usuario_id = _cache_usuario_integracao.get(EMAIL_USUARIO_INTEGRACAO)
        if usuario_id is not None:
            return usuario_id

        usuario = await SqlAlchemyUsuarioRepository(self._session).buscar_por_email(
            EMAIL_USUARIO_INTEGRACAO
        )
        if usuario is None:
            raise UsuarioIntegracaoNaoEncontrado(
                f"Usuário de integração '{EMAIL_USUARIO_INTEGRACAO}' não encontrado — "
                "rode `python -m amactive.scripts.bootstrap_usuario_integracao` antes de "
                "processar pedidos externos."
            )
        _cache_usuario_integracao[EMAIL_USUARIO_INTEGRACAO] = usuario.id
        return usuario.id
