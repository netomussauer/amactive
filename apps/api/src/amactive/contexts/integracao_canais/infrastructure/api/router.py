"""Controller (FastAPI APIRouter) do contexto Integração de Canais.

`POST /integracoes/nuvemshop/webhooks` é o ÚNICO endpoint público (sem JWT)
de todo o AMACTIVE — exceção explícita à regra `security: [bearerAuth: []]`
global de `docs/openapi.yaml` (documentar `security: []` só nesta rota).
Nenhuma dependency de autenticação (`Depends(get_current_user)`/
`requer_papel(...)`) é usada neste módulo — ausência deliberada, não um
descuido: é o mesmo padrão já usado por `POST /auth/login`
(`identidade/infrastructure/api/router.py`), o único outro endpoint público
do sistema hoje. Nenhum outro router é afetado — a autenticação de todas as
outras rotas continua exigida individualmente por cada endpoint (não há
dependency global aplicada em `main.py`), então esta exceção nunca enfraquece
nenhuma outra rota.

Controller thin, sem lógica de negócio — segue exatamente os passos de
design §5.1:
1. Lê o corpo bruto (`await request.body()`) ANTES de qualquer parsing
   Pydantic — a verificação HMAC precisa dos bytes exatos recebidos.
2. Obtém a `CredencialCanal` ativa (com cache curto em memória — ver
   `_TTL_CACHE_CREDENCIAL_SEGUNDOS`) para ter o `client_secret` decifrado.
3. Verifica a assinatura HMAC do header `x-linkedstore-hmac-sha256` — falha
   (ou credencial ausente) levanta `AssinaturaWebhookInvalida` (401) com
   mensagem única, sem tocar o banco além da leitura da credencial
   (nenhum `INSERT`/`COMMIT`).
4. Faz o parse do payload mínimo (`WebhookRecebidoRequest`; corpo inválido
   -> 422) e confere que `store_id` é o da credencial configurada.
5. `RegistrarWebhookCommand.executar(...)`.
6. Responde `200` sempre — evento novo ou duplicado, sem processar nenhuma
   lógica de negócio nesta requisição (isso é `ProcessarWebhookPedidoUseCase`,
   executado assincronamente pelo worker).
"""

from __future__ import annotations

import json
import time
from typing import Final

import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.integracao_canais.application.use_cases.registrar_webhook import (
    RegistrarWebhookCommand,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.domain.exceptions import AssinaturaWebhookInvalida
from amactive.contexts.integracao_canais.domain.repositories import CredencialDecifrada
from amactive.contexts.integracao_canais.infrastructure.api.schemas import (
    WebhookRecebidoRequest,
    WebhookRecebidoResponse,
)
from amactive.contexts.integracao_canais.infrastructure.metrics import (
    webhook_evento_recebido_total,
)
from amactive.contexts.integracao_canais.infrastructure.nuvemshop.webhook_verifier import (
    HmacSha256WebhookVerifier,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyCredencialCanalRepository,
    SqlAlchemyWebhookEventoRepository,
)
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.exceptions import ErroDeValidacao

router = APIRouter(prefix="/integracoes/nuvemshop", tags=["Integração Nuvemshop"])

# Header documentado pela Nuvemshop para a assinatura HMAC-SHA256 do corpo
# bruto do webhook — ver avaliação §1.4 / design §5.1.
_HEADER_ASSINATURA_HMAC = "x-linkedstore-hmac-sha256"

_verificador = HmacSha256WebhookVerifier()

_logger = structlog.get_logger(__name__)

# Resposta ÚNICA para toda falha de autenticação deste endpoint anônimo
# (assinatura ausente/errada, credencial não configurada, `store_id` de
# outra loja): nenhum detalhe distinguível revela o estado da integração a
# quem não tem o segredo. O motivo real vai para o log do servidor.
_DETALHE_NAO_AUTENTICADO: Final = "Assinatura HMAC do webhook não confere."

# Cache em memória (por processo) do resultado de `buscar_token_decifrado`.
# Este endpoint é anônimo e a leitura da credencial roda `pgp_sym_decrypt`
# no Postgres compartilhado ANTES de validar o HMAC — sem cache, cada
# requisição forjada custaria uma conexão de pool + 2 decifragens (um flood
# anônimo esgotaria o pool também da API autenticada). Com o cache, o flood
# não gera nenhuma consulta. Custo: uma rotação de credencial
# (`configurar_credencial_nuvemshop`) leva até este TTL para valer aqui.
# Guarda também "credencial ausente" (`None`) pelo mesmo motivo.
_TTL_CACHE_CREDENCIAL_SEGUNDOS: Final = 30.0
_cache_credencial: tuple[float, CredencialDecifrada | None] | None = None


def limpar_cache_credencial() -> None:
    """Invalida o cache de credencial — usado por testes (cada teste
    insere/remove `credencial_canal` na sua própria transação)."""
    global _cache_credencial
    _cache_credencial = None


async def _obter_credencial(session: AsyncSession) -> CredencialDecifrada | None:
    global _cache_credencial
    agora = time.monotonic()
    if _cache_credencial is not None and agora < _cache_credencial[0]:
        return _cache_credencial[1]
    credencial = await SqlAlchemyCredencialCanalRepository(session).buscar_token_decifrado(
        CanalIntegracao.NUVEMSHOP
    )
    _cache_credencial = (agora + _TTL_CACHE_CREDENCIAL_SEGUNDOS, credencial)
    return credencial


@router.post("/webhooks", response_model=WebhookRecebidoResponse, status_code=status.HTTP_200_OK)
async def receber_webhook(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> WebhookRecebidoResponse:
    corpo_bruto = await request.body()

    credencial = await _obter_credencial(session)
    if credencial is None:
        _logger.error("webhook.credencial_canal_ausente")
        raise AssinaturaWebhookInvalida(_DETALHE_NAO_AUTENTICADO)

    assinatura = request.headers.get(_HEADER_ASSINATURA_HMAC, "")
    assinatura_valida = _verificador.verificar(
        corpo_bruto=corpo_bruto, assinatura=assinatura, client_secret=credencial.client_secret
    )
    if not assinatura_valida:
        raise AssinaturaWebhookInvalida(_DETALHE_NAO_AUTENTICADO)

    # Daqui em diante o chamador conhece o `client_secret` (autenticado), mas
    # o corpo ainda pode estar malformado — 422 (nunca 500 com traceback).
    # `ValueError` cobre JSONDecodeError, UnicodeDecodeError e o
    # ValidationError do Pydantic (todos subclasses).
    try:
        payload_bruto = json.loads(corpo_bruto)
        payload = WebhookRecebidoRequest.model_validate(payload_bruto)
    except ValueError as exc:
        raise ErroDeValidacao("Corpo do webhook inválido.") from exc

    # O `client_secret` é do APP, não da loja: um evento corretamente
    # assinado mas de outra loja com o app instalado passaria no HMAC.
    if payload.store_id != credencial.store_id:
        _logger.warning("webhook.store_id_divergente")
        raise AssinaturaWebhookInvalida(_DETALHE_NAO_AUTENTICADO)

    # Métrica `webhook_evento_recebido_total{tipo_evento}` (design §8) —
    # todo webhook autenticado conta aqui, novo ou duplicado (a
    # idempotência é uma decisão de `registrar_se_novo`, não desta métrica).
    webhook_evento_recebido_total.labels(tipo_evento=payload.event).inc()

    webhook_repo = SqlAlchemyWebhookEventoRepository(session)
    await RegistrarWebhookCommand(webhook_repo).executar(
        canal=CanalIntegracao.NUVEMSHOP,
        tipo_evento=payload.event,
        id_recurso_externo=str(payload.id),
        payload_bruto=payload_bruto,
    )
    await session.commit()

    return WebhookRecebidoResponse()
