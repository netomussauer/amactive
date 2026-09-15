"""Testes de contrato do client HTTP da Nuvemshop — usam
`httpx.MockTransport` (já parte de `httpx`, dependência principal do
projeto desde este passo) para simular respostas da API sem rede real, ver
docs/design-integracao-nuvemshop.md §9 passo 5 ("testes de contrato usando
mocks/fixtures gravadas da API real, sem depender da Nuvemshop estar
acessível em CI")."""

from __future__ import annotations

import time
from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    ProdutoParaPublicacao,
    VarianteParaPublicacao,
)
from amactive.contexts.integracao_canais.infrastructure.nuvemshop.client import (
    NUVEMSHOP_API_VERSION,
    NuvemshopHttpClient,
    TokenBucketRateLimiter,
)

pytestmark = pytest.mark.unit

# Rate limiter "sem limite prático" para testes que não são sobre o próprio
# rate limiter — evita qualquer sleep real atrasando o teste.
_LIMITER_SEM_ESPERA = TokenBucketRateLimiter(rate=1000.0, capacity=1000)


def _client_com_transporte(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    rate_limiter: TokenBucketRateLimiter | None = None,
) -> NuvemshopHttpClient:
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return NuvemshopHttpClient(
        store_id="123456",
        access_token="token-permanente-do-app-privado",
        http_client=http_client,
        rate_limiter=rate_limiter or _LIMITER_SEM_ESPERA,
    )


# ── buscar_pedido ──
async def test_buscar_pedido_sucesso_mapeia_dto_com_headers_corretos() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/{NUVEMSHOP_API_VERSION}/123456/orders/999"
        assert request.headers["Authorization"] == "Bearer token-permanente-do-app-privado"
        assert request.headers["User-Agent"] == "AMACTIVE (contato@amactive.dev)"
        return httpx.Response(
            200,
            json={
                "id": 999,
                "customer": {
                    "id": 1,
                    "name": "Ana Compradora",
                    "email": "ana@example.com",
                },
                "products": [
                    {"product_id": 10, "variant_id": 20, "quantity": 2},
                ],
                "total": "150.00",
            },
        )

    client = _client_com_transporte(handler)

    pedido = await client.buscar_pedido("999")

    assert pedido.pedido_externo_id == "999"
    assert pedido.cliente_email == "ana@example.com"
    assert pedido.valor_total == Decimal("150.00")
    assert len(pedido.itens) == 1
    assert pedido.itens[0].variante_externo_id == "20"


# ── 429 ──
async def test_buscar_pedido_com_429_levanta_nuvemshop_indisponivel() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"x-rate-limit-reset": "5"})

    client = _client_com_transporte(handler)

    with pytest.raises(NuvemshopIndisponivel) as exc_info:
        await client.buscar_pedido("999")

    assert exc_info.value.status_code_origem == 429


async def test_429_com_x_rate_limit_reset_atrasa_proxima_aquisicao_de_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"x-rate-limit-reset": "5"})

    limiter = TokenBucketRateLimiter(rate=2.0, capacity=1)
    client = _client_com_transporte(handler, rate_limiter=limiter)

    with pytest.raises(NuvemshopIndisponivel):
        await client.buscar_pedido("999")

    tempos_de_espera: list[float] = []

    class _PararLoopDeTeste(Exception):
        pass

    async def _sleep_espiao(segundos: float) -> None:
        tempos_de_espera.append(segundos)
        # Não dorme de verdade — interrompe o loop de `adquirir()` assim
        # que capturamos o primeiro tempo de espera calculado, mantendo o
        # teste determinístico e rápido.
        raise _PararLoopDeTeste

    monkeypatch.setattr(
        "amactive.contexts.integracao_canais.infrastructure.nuvemshop.client.asyncio.sleep",
        _sleep_espiao,
    )

    with pytest.raises(_PararLoopDeTeste):
        await limiter.adquirir()

    assert tempos_de_espera
    # `atrasar_proxima_liberacao(5)` zera os tokens e congela o bucket por
    # ~5s — a próxima `adquirir()` deve calcular uma espera próxima disso
    # (tolerância generosa para não ficar flaky).
    assert 4.5 <= tempos_de_espera[0] <= 5.5


# ── erro genérico 4xx/5xx ──
async def test_erro_5xx_levanta_nuvemshop_indisponivel_com_status_origem() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="erro interno da Nuvemshop")

    client = _client_com_transporte(handler)

    with pytest.raises(NuvemshopIndisponivel) as exc_info:
        await client.buscar_pedido("999")

    assert exc_info.value.status_code_origem == 500


async def test_falha_de_rede_levanta_nuvemshop_indisponivel() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada", request=request)

    client = _client_com_transporte(handler)

    with pytest.raises(NuvemshopIndisponivel):
        await client.buscar_pedido("999")


# ── criar_produto / atualizar_produto ──
def _produto_para_publicacao() -> ProdutoParaPublicacao:
    return ProdutoParaPublicacao(
        produto_id=uuid4(),
        nome="Legging Fitness",
        descricao="Legging de alta compressão",
        variantes=[
            VarianteParaPublicacao(
                variante_id=uuid4(),
                sku="SKU-1",
                tamanho="M",
                cor="Preto",
                preco_venda=Decimal("99.90"),
            )
        ],
    )


async def test_criar_produto_envia_payload_e_mapeia_resultado() -> None:
    produto = _produto_para_publicacao()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/{NUVEMSHOP_API_VERSION}/123456/products"
        return httpx.Response(201, json={"id": 555, "variants": [{"id": 777, "sku": "SKU-1"}]})

    client = _client_com_transporte(handler)

    resultado = await client.criar_produto(produto)

    assert resultado.produto_externo_id == "555"
    assert resultado.variantes_externo_id[str(produto.variantes[0].variante_id)] == "777"


# ── atualizar_estoque_variante ──
async def test_atualizar_estoque_variante_monta_o_path_com_produto_e_variante() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == f"/{NUVEMSHOP_API_VERSION}/123456/products/10/variants/20"
        assert request.content == b'{"stock":5}'
        return httpx.Response(200, json={"id": 20, "stock": 5})

    client = _client_com_transporte(handler)

    await client.atualizar_estoque_variante(
        produto_externo_id="10", variante_externo_id="20", quantidade=5
    )


# ── TokenBucketRateLimiter — teste de tempo real ──
async def test_rate_limiter_limita_taxa_de_aquisicao_de_tokens() -> None:
    limiter = TokenBucketRateLimiter(rate=10.0, capacity=1)

    inicio = time.monotonic()
    for _ in range(3):
        await limiter.adquirir()
    decorrido = time.monotonic() - inicio

    # capacity=1: a 1ª aquisição é imediata (bucket cheio); as duas
    # seguintes exigem ~0.1s cada (rate=10 tokens/s) — tolerância generosa
    # para não ficar flaky em CI, mas alta o suficiente para provar que
    # houve throttling real (não seria possível em ~0s sem o limiter).
    assert decorrido >= 0.15
    assert decorrido < 2.0
