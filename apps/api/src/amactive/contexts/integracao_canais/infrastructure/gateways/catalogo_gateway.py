"""Implementa `CatalogoIntegracaoPort` (`domain/repositories.py`), SOMENTE
LEITURA — ver docs/design-integracao-nuvemshop.md §3.2.

Instancia os mesmos Protocols já publicados por Catálogo & Estoque
(`ProdutoRepository`/`VarianteRepository`/`ImagemRepository`/
`EstoqueRepository`) para montar `ProdutoParaPublicacao`. Nunca chama
`ProdutoRepository.criar/atualizar` nem `MovimentacaoRepository.registrar` —
a baixa/ajuste de estoque, mesmo quando originada por um pedido Nuvemshop,
sempre passa por `EstoquePort.registrar_saida_venda` dentro de
`CriarPedidoUseCase` (via `vendas_gateway.py`), nunca por aqui.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyEstoqueRepository,
    SqlAlchemyImagemRepository,
    SqlAlchemyProdutoRepository,
    SqlAlchemyVarianteRepository,
)
from amactive.contexts.integracao_canais.domain.exceptions import (
    ProdutoNaoEncontradoParaPublicacao,
)
from amactive.contexts.integracao_canais.domain.repositories import (
    ImagemParaPublicacao,
    ProdutoParaPublicacao,
    VarianteParaPublicacao,
)
from amactive.shared_kernel.money import aplicar_desconto_percentual


class CatalogoIntegracaoGateway:
    """Implementa `CatalogoIntegracaoPort` — ver docstring do módulo."""

    def __init__(self, session: AsyncSession) -> None:
        self._produtos = SqlAlchemyProdutoRepository(session)
        self._variantes = SqlAlchemyVarianteRepository(session)
        self._imagens = SqlAlchemyImagemRepository(session)
        self._estoque = SqlAlchemyEstoqueRepository(session)

    async def buscar_produto_para_publicacao(self, produto_id: UUID) -> ProdutoParaPublicacao:
        produto = await self._produtos.buscar_por_id(produto_id)
        if produto is None:
            raise ProdutoNaoEncontradoParaPublicacao(
                f"Produto {produto_id} não encontrado para publicação na Nuvemshop."
            )

        variantes = await self._variantes.listar_por_produto(produto_id)
        imagens = await self._imagens.listar_por_produto(produto_id)

        variantes_para_publicacao = [
            VarianteParaPublicacao(
                variante_id=variante.id,
                sku=variante.sku,
                tamanho=variante.tamanho,
                cor=variante.cor,
                # Preço/promoção já calculados (design §3.2) — o desconto
                # percentual do produto (quando ativo, ver docs/data-model.md
                # decisão #14) é aplicado aqui, não deixado para a Nuvemshop
                # replicar a lógica de promoção do AMACTIVE.
                preco_venda=(
                    aplicar_desconto_percentual(variante.preco_venda, produto.desconto_percentual)
                    if produto.desconto_percentual is not None
                    else variante.preco_venda
                ),
            )
            for variante in variantes
            if variante.ativo
        ]
        imagens_para_publicacao = [
            ImagemParaPublicacao(
                cor=imagem.cor, url=imagem.url, ordem=imagem.ordem, principal=imagem.principal
            )
            for imagem in imagens
        ]

        return ProdutoParaPublicacao(
            produto_id=produto.id,
            nome=produto.nome,
            descricao=produto.descricao,
            variantes=variantes_para_publicacao,
            imagens=imagens_para_publicacao,
        )

    async def buscar_saldo_estoque(self, variante_id: UUID) -> int:
        estoque = await self._estoque.buscar_por_variante(variante_id)
        return estoque.quantidade if estoque is not None else 0
