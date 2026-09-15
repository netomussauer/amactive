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
2. Busca a `CredencialCanal` ativa para obter o `client_secret` decifrado.
3. Verifica a assinatura HMAC do header `x-linkedstore-hmac-sha256` — falha
   levanta `AssinaturaWebhookInvalida` (401) sem tocar o banco além da
   leitura da credencial (nenhum `INSERT`/`COMMIT`).
4. Faz o parse do payload mínimo (`WebhookRecebidoRequest`).
5. `RegistrarWebhookCommand.executar(...)`.
6. Responde `200` sempre — evento novo ou duplicado, sem processar nenhuma
   lógica de negócio nesta requisição (isso é `ProcessarWebhookPedidoUseCase`,
   executado assincronamente pelo worker).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.integracao_canais.application.use_cases.registrar_webhook import (
    RegistrarWebhookCommand,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.domain.exceptions import (
    AssinaturaWebhookInvalida,
    CredencialCanalAusente,
)
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

router = APIRouter(prefix="/integracoes/nuvemshop", tags=["Integração Nuvemshop"])

# Header documentado pela Nuvemshop para a assinatura HMAC-SHA256 do corpo
# bruto do webhook — ver avaliação §1.4 / design §5.1.
_HEADER_ASSINATURA_HMAC = "x-linkedstore-hmac-sha256"

_verificador = HmacSha256WebhookVerifier()


@router.post("/webhooks", response_model=WebhookRecebidoResponse, status_code=status.HTTP_200_OK)
async def receber_webhook(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> WebhookRecebidoResponse:
    corpo_bruto = await request.body()

    credencial_repo = SqlAlchemyCredencialCanalRepository(session)
    credencial = await credencial_repo.buscar_token_decifrado(CanalIntegracao.NUVEMSHOP)
    if credencial is None:
        raise CredencialCanalAusente(
            "Nenhuma credencial NUVEMSHOP configurada — impossível verificar a assinatura "
            "do webhook."
        )

    assinatura = request.headers.get(_HEADER_ASSINATURA_HMAC, "")
    assinatura_valida = _verificador.verificar(
        corpo_bruto=corpo_bruto, assinatura=assinatura, client_secret=credencial.client_secret
    )
    if not assinatura_valida:
        raise AssinaturaWebhookInvalida("Assinatura HMAC do webhook não confere.")

    payload_bruto = json.loads(corpo_bruto)
    payload = WebhookRecebidoRequest.model_validate(payload_bruto)

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
