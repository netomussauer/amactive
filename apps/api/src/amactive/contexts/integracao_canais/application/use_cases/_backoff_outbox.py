"""Política de retry/backoff compartilhada pelos dois outbox (estoque e
catálogo) — ver docs/design-integracao-nuvemshop.md §4.3.

Extraída de `publicar_estoque_canal.py` (passo 7) para este módulo interno
(prefixo `_`, não é uma porta pública do contexto) quando `publicar_catalogo_canal.py`
(passo 8) precisou exatamente da mesma lógica — os dois outbox divergem
apenas em qual entidade/repositório eles processam, nunca na política de
retry em si (mesmo teto de tentativas, mesmo backoff exponencial + jitter,
mesmo tratamento de 4xx vs. 5xx/429), então uma única implementação
compartilhada evita duas cópias divergindo silenciosamente com o tempo.

Retry/backoff (design §4.3, mesmo princípio já fixado em docs/SDD.md §5.2 —
"nunca retry para 4xx"): erro de rede/5xx/429 (`NuvemshopIndisponivel` sem
`status_code_origem` 4xx-não-429) agenda nova tentativa com backoff
exponencial + jitter (tentativa 1 -> 2s, tentativa 2 -> 4s, tentativa 3 ->
8s, ±20%), até um teto de `MAX_TENTATIVAS_OUTBOX = 8` tentativas. Erros 4xx
(exceto 429) e o teto de tentativas esgotado são tratados como falha
definitiva: a linha permanece `status=ERRO`, mas `proxima_tentativa_em` é
empurrada bem além de qualquer janela de retry legítima (ano 2999) — nunca
mais reconsiderada automaticamente pela janela `proxima_tentativa_em <=
now()` das consultas de coalescing (design §4.2), até intervenção manual.

Nota técnica sobre a sentinela: deliberadamente NÃO se usa `datetime.max`
(ano 9999) — o `asyncpg` trata esse valor exato como caso especial e o
grava como `infinity` do Postgres, que ao ser lido de volta perde o
`tzinfo` (`datetime` *naive*), quebrando qualquer comparação posterior com
um `datetime` *aware*. Ano 2999 está tão além de qualquer janela de retry
real quanto `datetime.max` para os fins práticos deste outbox, sem cair
nesse caso especial do driver.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Final

from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel

# Teto de tentativas antes de desistir definitivamente de uma linha (design
# §4.3) — depois disso, `proxima_tentativa_em` é empurrada para
# `SEM_REPROCESSAMENTO_AUTOMATICO`, fora da janela que as consultas de
# coalescing (§4.2) reconsideram.
MAX_TENTATIVAS_OUTBOX: Final = 8

# tentativa 1 -> 2s, tentativa 2 -> 4s, tentativa 3 -> 8s (design §4.3).
_BACKOFF_BASE_SEGUNDOS: Final = 2.0
_BACKOFF_JITTER_FRACAO: Final = 0.20

# Sentinela de "nunca mais reprocessar automaticamente" — usado tanto para o
# teto de tentativas esgotado quanto para erros 4xx não retentáveis (design
# §4.3). Nunca satisfaz `proxima_tentativa_em <= now()` das queries de
# coalescing. Ver nota técnica no docstring do módulo sobre por que NÃO é
# `datetime.max` (interação com o tratamento de `infinity` do asyncpg).
SEM_REPROCESSAMENTO_AUTOMATICO: Final = datetime(2999, 1, 1, tzinfo=UTC)


def calcular_backoff_segundos(tentativa: int) -> float:
    """tentativa 1 -> 2s, tentativa 2 -> 4s, tentativa 3 -> 8s (design
    §4.3), com jitter de ±20% — evita sincronizar retries de múltiplas
    réplicas do worker no mesmo instante."""
    base = _BACKOFF_BASE_SEGUNDOS * (2 ** (tentativa - 1))
    jitter = base * _BACKOFF_JITTER_FRACAO
    return base + random.uniform(-jitter, jitter)


def eh_erro_4xx_nao_retentavel(exc: NuvemshopIndisponivel) -> bool:
    """4xx exceto 429 nunca é retentado automaticamente (design §4.3, mesmo
    princípio de docs/SDD.md §5.2: "nunca retry para 4xx") — um payload
    malformado não se corrige sozinho reenviando."""
    codigo = exc.status_code_origem
    return codigo is not None and 400 <= codigo < 500 and codigo != 429


def calcular_proxima_tentativa_em(
    *, tentativas_apos_esta_falha: int, exc: NuvemshopIndisponivel
) -> datetime:
    """Decide o valor de `proxima_tentativa_em` a gravar via
    `marcar_erro_com_retry` após uma falha — já encapsula a escolha entre
    backoff normal e a sentinela de falha definitiva (design §4.3), para que
    os dois outbox nunca precisem duplicar essa decisão."""
    falha_definitiva = (
        eh_erro_4xx_nao_retentavel(exc) or tentativas_apos_esta_falha >= MAX_TENTATIVAS_OUTBOX
    )
    if falha_definitiva:
        return SEM_REPROCESSAMENTO_AUTOMATICO

    atraso_segundos = calcular_backoff_segundos(tentativas_apos_esta_falha)
    return datetime.now(UTC) + timedelta(seconds=atraso_segundos)
