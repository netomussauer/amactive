"""ACL do client HTTP da Nuvemshop — implementa `NuvemshopClientPort`
(`domain/repositories.py`), ver docs/design-integracao-nuvemshop.md §7.

Componentes:
- `TokenBucketRateLimiter`: rate limiter local (§7.3), compartilhado por
  todo o processo via `RATE_LIMITER_PADRAO`.
- `NuvemshopHttpClient`: `httpx.AsyncClient` autenticado por token
  permanente de app privado (avaliação §1.1), versão de API fixada em
  código (nunca env var, §7.1), com tradução de erros HTTP para
  `NuvemshopIndisponivel`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Final

import httpx

from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    NuvemshopPedidoDTO,
    ProdutoParaPublicacao,
    PublicacaoResultado,
)
from amactive.contexts.integracao_canais.infrastructure.metrics import (
    nuvemshop_client_requisicoes_total,
)
from amactive.contexts.integracao_canais.infrastructure.nuvemshop.mappers import (
    mapear_pedido_nuvemshop,
    mapear_resultado_publicacao,
    montar_payload_produto,
)

# Rótulo sentinela para falhas de rede sem resposta HTTP (timeout, conexão
# recusada) — nenhum `status_code` HTTP existe nesse caso (design §8).
_STATUS_CODE_ERRO_REDE: Final = "erro_rede"

# Fixada em código, nunca lida de variável de ambiente (design §7.1) — uma
# mudança de versão da API da Nuvemshop deve ser sempre uma decisão de
# código revisada, não um efeito colateral de configuração.
NUVEMSHOP_API_VERSION: Final = "2025-03"

# Header User-Agent é obrigatório — sua ausência retorna 400 (avaliação
# §1.1). Placeholder razoável, documentadamente configurável no futuro (ex.:
# via Settings) caso a Nuvemshop passe a exigir um endereço de fato
# monitorado; hoje só precisa satisfazer a exigência de presença/formato do
# header.
_EMAIL_CONTATO_USER_AGENT: Final = "contato@amactive.dev"

_TIMEOUT_PADRAO_SEGUNDOS: Final = 30.0


class TokenBucketRateLimiter:
    """Token bucket em memória, pensado para ser um único objeto
    compartilhado por todo o processo worker (design §7.3/§4.4): o limite
    da Nuvemshop é por loja+app, não por tipo de operação, então tanto o
    outbox de estoque quanto o de catálogo quanto o `GET /orders/{id}` do
    processamento de webhook devem disputar o mesmo bucket.

    `rate` tokens/s são reabastecidos continuamente até `capacity` —
    espelha o Leaky Bucket documentado pela Nuvemshop (avaliação §1.5):
    2 req/s sustentadas, burst de 40.
    """

    def __init__(self, rate: float = 2.0, capacity: int = 40) -> None:
        self._rate = rate
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._ultima_atualizacao = time.monotonic()
        self._lock = asyncio.Lock()

    async def adquirir(self) -> None:
        """Bloqueia até haver 1 token disponível, então o consome."""
        while True:
            async with self._lock:
                self._reabastecer()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                agora = time.monotonic()
                # Tempo restante até o bucket sair do estado "congelado" por
                # `atrasar_proxima_liberacao` (0 se não houver congelamento
                # ativo), somado ao tempo normal de acúmulo de 1 token.
                congelado_restante = max(0.0, self._ultima_atualizacao - agora)
                faltam = congelado_restante + (1 - self._tokens) / self._rate
            await asyncio.sleep(faltam)

    async def atrasar_proxima_liberacao(self, segundos: float) -> None:
        """Defesa adicional contra `429` (design §7.3): zera os tokens
        disponíveis e empurra o próximo reabastecimento `segundos` à frente,
        para que `adquirir()` só volte a liberar depois que o servidor
        sinalizou (via `x-rate-limit-reset`) que o bucket real deveria ter
        sido reposto.

        Limitação documentada: isso é uma heurística local de "recuar o
        relógio interno", não uma sincronização formal com o estado exato
        do bucket do servidor (que também depende de outras requisições
        concorrentes fora do nosso controle, ex.: outra réplica do worker)
        — é suficiente como defesa *adicional* à política de retry do
        outbox (§4.3), não uma garantia de nunca mais receber `429`.
        """
        if segundos <= 0:
            return
        async with self._lock:
            self._tokens = 0.0
            self._ultima_atualizacao = time.monotonic() + segundos

    def _reabastecer(self) -> None:
        agora = time.monotonic()
        decorrido = agora - self._ultima_atualizacao
        if decorrido <= 0:
            # `_ultima_atualizacao` está no futuro — ainda dentro da janela
            # congelada por `atrasar_proxima_liberacao` (ou nenhum tempo
            # passou). Não reabastece nem move `_ultima_atualizacao` para
            # trás: fazer isso apagaria o congelamento no primeiro
            # `adquirir()` chamado logo em seguida, em vez de só liberar
            # depois que `segundos` de fato decorrerem.
            return
        self._tokens = min(self._capacity, self._tokens + decorrido * self._rate)
        self._ultima_atualizacao = agora


# Instância única por processo — todo `NuvemshopHttpClient` criado sem um
# `rate_limiter` explícito compartilha este bucket (design §4.4/§7.3).
RATE_LIMITER_PADRAO: Final = TokenBucketRateLimiter()


def _ler_rate_limit_reset(headers: httpx.Headers) -> float | None:
    """Lê `x-rate-limit-reset` (avaliação §1.5). Assumido como segundos até
    o bucket da Nuvemshop ser reabastecido — padrão comum em APIs com leaky
    bucket, ainda que a documentação pesquisada (avaliação §1.5) não
    detalhe explicitamente a unidade do valor.

    Limitação documentada (design §7.3): é uma heurística de defesa
    adicional, não uma sincronização formal — se a unidade real não for
    segundos, o efeito prático é só um atraso local maior/menor do que o
    ideal, nunca uma falha (o valor nunca é usado para nada além de atrasar
    a próxima aquisição de token)."""
    valor = headers.get("x-rate-limit-reset")
    if valor is None:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


class NuvemshopHttpClient:
    """Implementa `NuvemshopClientPort` — ver design §7."""

    def __init__(
        self,
        *,
        store_id: str,
        access_token: str,
        http_client: httpx.AsyncClient | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> None:
        self._base_url = f"https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}/{store_id}"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": f"AMACTIVE ({_EMAIL_CONTATO_USER_AGENT})",
        }
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        self._limiter = rate_limiter if rate_limiter is not None else RATE_LIMITER_PADRAO

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO:
        payload = await self._request("GET", f"/orders/{pedido_externo_id}")
        return mapear_pedido_nuvemshop(payload)

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        payload = await self._request("POST", "/products", json=montar_payload_produto(produto))
        return mapear_resultado_publicacao(payload, produto)

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado:
        payload = await self._request(
            "PUT", f"/products/{produto_externo_id}", json=montar_payload_produto(produto)
        )
        return mapear_resultado_publicacao(payload, produto)

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        await self._request(
            "PUT",
            f"/products/{produto_externo_id}/variants/{variante_externo_id}",
            json={"stock": quantidade},
        )

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        await self._limiter.adquirir()
        try:
            resposta = await self._http.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers,
                json=json,
                timeout=_TIMEOUT_PADRAO_SEGUNDOS,
            )
        except httpx.HTTPError as exc:
            # Métrica `nuvemshop_client_requisicoes_total{status_code}`
            # (design §8) — todo request passa por aqui, inclusive falhas de
            # rede sem resposta HTTP (rótulo sentinela `erro_rede`).
            nuvemshop_client_requisicoes_total.labels(status_code=_STATUS_CODE_ERRO_REDE).inc()
            raise NuvemshopIndisponivel(
                f"Falha de rede ao chamar {method} {path} na Nuvemshop: {exc}"
            ) from exc

        nuvemshop_client_requisicoes_total.labels(status_code=str(resposta.status_code)).inc()

        if resposta.status_code == 429:
            reset = _ler_rate_limit_reset(resposta.headers)
            if reset is not None:
                await self._limiter.atrasar_proxima_liberacao(reset)
            # A política de retry propriamente dita (backoff exponencial do
            # outbox) é responsabilidade de um passo futuro (7/8, design
            # §4.3) — este client só propaga o erro e ajusta o rate limiter
            # local como defesa adicional (§7.3).
            raise NuvemshopIndisponivel(
                f"Rate limit da Nuvemshop excedido em {method} {path} (429).",
                status_code_origem=429,
            )

        if resposta.status_code >= 400:
            raise NuvemshopIndisponivel(
                f"Nuvemshop respondeu {resposta.status_code} para {method} {path}: {resposta.text}",
                status_code_origem=resposta.status_code,
            )

        if not resposta.content:
            return {}
        return dict(resposta.json())
