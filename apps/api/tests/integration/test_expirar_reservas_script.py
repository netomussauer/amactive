"""Reproduz, em um processo Python isolado, o bug real achado no infra-lab
(2026-10-23): o CronJob `expirar-reservas` falhava com
`sqlalchemy.exc.NoReferencedTableError` sempre que havia pelo menos um
pedido PENDENTE com reserva vencida para cancelar.

Precisa rodar em subprocesso, não in-process: `tests/integration/conftest.py`
já faz `import amactive.main` (de propósito, ver comentário lá) antes de
qualquer teste rodar, o que registra TODAS as tabelas em `Base.metadata` só
por isso — um teste in-process neste mesmo processo pytest nunca conseguiria
reproduzir o bug, porque o registro incompleto que o causa já teria sido
"corrigido" de lado pelo import do conftest antes mesmo deste arquivo ser
coletado. O processo real do CronJob em produção, por outro lado, só executa
`python -m amactive.scripts.expirar_reservas` — nunca importa `main.py` nem
nada do conftest.

Por que precisa de um pedido vencido de verdade (não basta o script rodar
contra um banco vazio): o repro empírico mostrou que `NoReferencedTableError`
só é levantado dentro de `Session.flush()`, no passo em que o SQLAlchemy
ordena as tabelas por dependência de FK (`Mapper._sorted_tables`,
`sort_tables_and_constraints`) para decidir a ordem do INSERT/UPDATE — isso
só acontece quando `ExpirarReservasVencidasUseCase.atualizar_status` de fato
muda e salva um `PedidoModel`. Contra um banco sem nenhuma reserva vencida, o
laço nunca chama `flush()` e o script "funciona" mesmo sem o fix, mascarando
o bug.

A linha de `pedido` é inserida/removida via asyncpg direto (mesmo padrão de
`conftest._aplicar_migrations`) com commit real — precisa ser visível para o
subprocesso, que abre sua própria conexão; a fixture `db_session` (savepoint
revertido no teardown) não serviria aqui."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.conftest import TEST_DATABASE_URL, _asyncpg_dsn

pytestmark = pytest.mark.integration

_API_DIR = Path(__file__).resolve().parents[2]


def _python_do_venv() -> str:
    """Mesmo interpretador/venv usado para instalar o pacote `amactive` em
    modo editable (ver apps/api/README.md) — `sys.executable` por si só não
    é confiável aqui porque o processo do pytest pode estar rodando sob um
    `python` de fora do venv com o pacote instalado via outro mecanismo."""
    venv_python = _API_DIR / ".venv" / "bin" / "python"
    return str(venv_python) if venv_python.exists() else sys.executable


@pytest_asyncio.fixture
async def pedido_vitrine_com_reserva_vencida(test_engine: AsyncEngine):
    """Insere (com commit real, fora do savepoint de `db_session`) um pedido
    PENDENTE da vitrine cuja reserva já venceu — exatamente o tipo de linha
    que `ExpirarReservasVencidasUseCase` precisa encontrar para acionar o
    bug. `test_engine` força a aplicação das migrations antes do insert."""
    conn = await asyncpg.connect(dsn=_asyncpg_dsn(TEST_DATABASE_URL))
    pedido_id = uuid.uuid4()
    try:
        await conn.execute(
            """
            INSERT INTO pedido (
                id, numero, cliente_id, usuario_id, status,
                subtotal, desconto, valor_total, criado_em,
                origem_canal, reservado_ate
            ) VALUES (
                $1, $2, NULL, NULL, 'PENDENTE',
                10.00, 0.00, 10.00, now(),
                'VITRINE', $3
            )
            """,
            pedido_id,
            f"TESTE-{uuid.uuid4().hex[:8].upper()}",
            datetime.now(UTC) - timedelta(minutes=1),
        )
        yield pedido_id
    finally:
        await conn.execute("DELETE FROM pedido WHERE id = $1", pedido_id)
        await conn.close()


async def test_script_expirar_reservas_roda_isolado_sem_erro_de_fk_cross_contexto(
    pedido_vitrine_com_reserva_vencida: uuid.UUID,
) -> None:
    pedido_id = pedido_vitrine_com_reserva_vencida

    # subprocess.run é bloqueante — roda numa thread para não travar o event
    # loop do teste (que também faz I/O assíncrono via asyncpg nesta função).
    resultado = await asyncio.to_thread(
        subprocess.run,
        [_python_do_venv(), "-m", "amactive.scripts.expirar_reservas"],
        cwd=_API_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    # Antes do fix (import de amactive.shared_kernel.all_models no topo do
    # script), isto falhava com exit code 1 e
    # "sqlalchemy.exc.NoReferencedTableError: Foreign key associated with
    # column 'pedido.usuario_id' could not find table 'usuario'" no stderr,
    # no meio do flush do primeiro pedido vencido encontrado.
    assert resultado.returncode == 0, resultado.stderr
    assert "NoReferencedTableError" not in resultado.stderr
    assert "1 pedido(s) da vitrine cancelado(s)" in resultado.stdout

    conn = await asyncpg.connect(dsn=_asyncpg_dsn(TEST_DATABASE_URL))
    try:
        status = await conn.fetchval("SELECT status FROM pedido WHERE id = $1", pedido_id)
    finally:
        await conn.close()
    assert status == "CANCELADO"
