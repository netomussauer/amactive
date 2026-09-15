"""DTOs do contexto Integração de Canais.

Os DTOs somente-leitura consumidos pelos Protocols de
`domain/repositories.py` (`NuvemshopPedidoDTO`, `ProdutoParaPublicacao`,
`PublicacaoResultado`, `EnderecoExterno`, `CredencialDecifrada`, ...) são
definidos ali mesmo — mesmo padrão já usado por
`vendas/domain/repositories.py` (`VarianteVenda`): DTOs que fazem parte da
assinatura de uma porta (Protocol) vivem junto da porta, no domínio, não na
camada de aplicação. Este módulo os reexporta para uso conveniente pelos
casos de uso (`application/use_cases/`), seguindo a estrutura de pastas de
docs/design-integracao-nuvemshop.md §2.2.

`ItemPedidoInput`/`PagamentoInput` já existem em
`vendas/application/dto.py` — reimportados aqui (não duplicados), pois
`ProcessarWebhookPedidoUseCase` monta esses mesmos DTOs para reaproveitar
`CriarPedidoUseCase` via `PedidoIntegracaoPort` (design §3.1).
"""

from __future__ import annotations

from amactive.contexts.integracao_canais.domain.repositories import (
    CredencialDecifrada,
    EnderecoExterno,
    ImagemParaPublicacao,
    ItemPedidoExternoDTO,
    NuvemshopPedidoDTO,
    ProdutoParaPublicacao,
    PublicacaoResultado,
    VarianteParaPublicacao,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput

__all__ = [
    "CredencialDecifrada",
    "EnderecoExterno",
    "ImagemParaPublicacao",
    "ItemPedidoExternoDTO",
    "ItemPedidoInput",
    "NuvemshopPedidoDTO",
    "PagamentoInput",
    "ProdutoParaPublicacao",
    "PublicacaoResultado",
    "VarianteParaPublicacao",
]
