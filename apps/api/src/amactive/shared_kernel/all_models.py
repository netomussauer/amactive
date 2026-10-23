"""Importa os módulos de modelos ORM de **todos** os contextos, só pelo
efeito colateral de registrar suas `Table`s em `Base.metadata`
(ver shared_kernel/database.py) antes de qualquer mapper ser configurado.

Por quê isso existe: `ForeignKey("tabela.coluna")` em string (o padrão usado
em todos os modelos deste projeto) só é resolvida de forma tardia, na
primeira vez que o mapper é configurado — não na importação da classe. Essa
resolução usa `Base.metadata.tables`, que só contém as tabelas cujo módulo de
modelos já foi importado *neste processo*, em algum momento, por qualquer
motivo.

A aplicação FastAPI (`main.py`) nunca teve esse problema: ela importa, direta
ou transitivamente, os routers de TODOS os contextos no boot, então toda
`Table` acaba registrada bem antes da primeira query. O mesmo vale para a
suíte de testes de integração (`tests/integration/conftest.py` importa
`amactive.main` inteiro de propósito, com o mesmo racional).

Scripts de entrypoint único (`amactive/scripts/*.py`), por outro lado,
importam só os módulos de que precisam — e nada garante que isso inclua o
dono de toda tabela referenciada por FK a partir dali. Foi assim que o
CronJob `expirar-reservas` (roda a cada 5min, ver
`amactive/scripts/expirar_reservas.py`) começou a falhar em produção com
`sqlalchemy.exc.NoReferencedTableError` na FK `pedido.cliente_id -> cliente`
(achado no infra-lab, 2026-10-23): o script só importa os contextos
`vendas`/`catalogo_estoque` (donos das tabelas que de fato usa), nunca
`cadastros` (dono de `cliente`) nem `identidade` (dono de `usuario`, outra FK
de `PedidoModel`) — ambos só chegam a ser importados quando a aplicação sobe
por inteiro via `main.py`, o que o processo do CronJob nunca faz.

Qualquer entrypoint que rode fora do boot completo do FastAPI — scripts,
workers, CronJobs — e toque um modelo com FK para outro contexto deve
importar este módulo (só pelo efeito colateral):

    import amactive.shared_kernel.all_models  # noqa: F401
"""

from __future__ import annotations

from amactive.contexts.cadastros.infrastructure.persistence import (
    models as _cadastros_models,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence import (
    models as _catalogo_estoque_models,
)
from amactive.contexts.identidade.infrastructure.persistence import (
    models as _identidade_models,
)
from amactive.contexts.integracao_canais.infrastructure.persistence import (
    models as _integracao_canais_models,
)
from amactive.contexts.vendas.infrastructure.persistence import (
    models as _vendas_models,
)

# Mantém os módulos "usados" para o linter — a importação em si é o que
# importa (efeito colateral de registro em Base.metadata), os nomes nunca
# são referenciados depois.
__all__ = [
    "_cadastros_models",
    "_catalogo_estoque_models",
    "_identidade_models",
    "_integracao_canais_models",
    "_vendas_models",
]
