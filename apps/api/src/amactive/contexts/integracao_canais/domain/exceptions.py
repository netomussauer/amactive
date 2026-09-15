"""Exceções de domínio do contexto Integração de Canais — ver
docs/design-integracao-nuvemshop.md §2.6.

Seguem o padrão de `shared_kernel/exceptions.py` (`DomainError` +
`status_code`/`type_slug`/`title`), igual a todos os outros contextos.
"""

from __future__ import annotations

from amactive.shared_kernel.exceptions import (
    ConflitoDeEstado,
    DomainError,
    EntidadeNaoEncontrada,
    ErroDeValidacao,
    NaoAutorizado,
)


class AssinaturaWebhookInvalida(NaoAutorizado):
    """HMAC não confere com o `client_secret` da credencial ativa."""


class VarianteNaoMapeada(ErroDeValidacao):
    """Item de pedido externo referencia um `variant_id` sem
    `MapeamentoVarianteCanal`."""


class CredencialCanalAusente(EntidadeNaoEncontrada):
    """Nenhuma `CredencialCanal` configurada para o canal — worker não pode
    operar."""


class PedidoExternoJaProcessado(ConflitoDeEstado):
    """`UNIQUE(origem_canal, pedido_externo_id)` violado — defesa em
    profundidade, ver docs/design-integracao-nuvemshop.md §3.1."""


class UsuarioIntegracaoNaoEncontrado(EntidadeNaoEncontrada):
    """O usuário de sistema que assina pedidos importados
    (`integracao.nuvemshop@sistema.amactive.internal`, ver
    `scripts/bootstrap_usuario_integracao.py`) ainda não foi provisionado —
    sem ele, nenhum pedido externo pode ser confirmado (design §3.1)."""


class ProdutoNaoEncontradoParaPublicacao(EntidadeNaoEncontrada):
    """`produto_id` referenciado não existe (mais) em Catálogo & Estoque —
    ver `infrastructure/gateways/catalogo_gateway.py` (design §3.2)."""


class NuvemshopIndisponivel(DomainError):
    """Erro de rede, `4xx` (exceto `429`, tratado pelo rate limiter — ver
    `infrastructure/nuvemshop/client.py`) ou `5xx` retornado pela API da
    Nuvemshop ao processar uma chamada do `NuvemshopClientPort` (design
    §7). `status_code` sempre `502` do ponto de vista do AMACTIVE
    (o erro é de um serviço upstream, não da requisição em si) —
    `status_code_origem` preserva o código HTTP original (quando houver)
    para a política de retry do outbox distinguir 4xx de 5xx/429 (design
    §4.3), que é responsabilidade de um passo futuro (7/8), não deste
    client."""

    status_code = 502
    type_slug = "nuvemshop-indisponivel"
    title = "Falha ao comunicar com a Nuvemshop"

    def __init__(self, detail: str, *, status_code_origem: int | None = None) -> None:
        super().__init__(detail)
        self.status_code_origem = status_code_origem
