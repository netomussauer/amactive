"""Registro MANUAL de pedidos por canal (PDV / WHATSAPP / NUVEMSHOP) via HTTP
(ASGI in-process, Postgres de teste real): `POST /pedidos` com `origem_canal` e
`pedido_externo_id`, duplicidade (409) sem baixar estoque duas vezes, filtro
`origem_canal` em `GET /pedidos` e em `GET /relatorios/vendas-por-periodo`, e
regressão do comportamento PDV.

Usa a sessão transacional isolada por teste (`db_session`, SAVEPOINT — ver
`tests/integration/conftest.py`) como override de `get_db_session`: nada do
que é criado aqui vaza para os outros testes nem se acumula no banco.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.vendas.domain.entities import OrigemCanalPedido
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
    violou_unicidade_pedido_externo,
)
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _criar_variante(
    client: AsyncClient, headers: dict[str, str], *, estoque_inicial: int = 10
) -> dict:
    produto_resp = await client.post(
        "/produtos",
        json={"nome": f"Top {uuid.uuid4().hex[:6]}", "marca": "AMACTIVE"},
        headers=headers,
    )
    assert produto_resp.status_code == 201, produto_resp.text
    variante_resp = await client.post(
        f"/produtos/{produto_resp.json()['id']}/variantes",
        json={
            "tamanho": "M",
            "cor": "Preto",
            "preco_venda": "100.00",
            "estoque_inicial": estoque_inicial,
        },
        headers=headers,
    )
    assert variante_resp.status_code == 201, variante_resp.text
    return variante_resp.json()


async def _estoque(client: AsyncClient, headers: dict[str, str], variante: dict) -> int:
    resp = await client.get(f"/variantes/{variante['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    return int(resp.json()["quantidade_estoque"])


async def _postar_pedido(
    client: AsyncClient,
    headers: dict[str, str],
    variante: dict,
    *,
    quantidade: int = 1,
    **extras: object,
):
    total = Decimal("100.00") * quantidade
    return await client.post(
        "/pedidos",
        json={
            "itens": [{"variante_id": variante["id"], "quantidade": quantidade}],
            "pagamentos": [{"forma_pagamento": "PIX", "valor": f"{total:.2f}"}],
            **extras,
        },
        headers=headers,
    )


def _numero_externo() -> str:
    return f"T-{uuid.uuid4().hex[:10]}"


# ── criação por canal ──
async def test_pdv_por_padrao_continua_identico_ao_comportamento_anterior(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=5)

    resp = await _postar_pedido(client, headers, variante, quantidade=2)

    assert resp.status_code == 201, resp.text
    pedido = resp.json()
    assert pedido["status"] == "CONFIRMADO"
    assert pedido["valor_total"] == "200.00"
    assert pedido["origem_canal"] == "PDV"
    assert pedido["pedido_externo_id"] is None
    assert await _estoque(client, headers, variante) == 3


async def test_pdv_explicito_e_aceito(client: AsyncClient, headers: dict[str, str]) -> None:
    variante = await _criar_variante(client, headers)

    resp = await _postar_pedido(client, headers, variante, origem_canal="PDV")

    assert resp.status_code == 201, resp.text
    assert resp.json()["origem_canal"] == "PDV"


async def test_whatsapp_sem_pedido_externo_id_baixa_estoque(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=10)

    resp = await _postar_pedido(client, headers, variante, quantidade=3, origem_canal="WHATSAPP")

    assert resp.status_code == 201, resp.text
    pedido = resp.json()
    assert pedido["origem_canal"] == "WHATSAPP"
    assert pedido["pedido_externo_id"] is None
    assert await _estoque(client, headers, variante) == 7


async def test_whatsapp_sem_numero_permite_varios_pedidos(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=10)

    primeiro = await _postar_pedido(client, headers, variante, origem_canal="WHATSAPP")
    segundo = await _postar_pedido(client, headers, variante, origem_canal="WHATSAPP")

    assert primeiro.status_code == 201, primeiro.text
    assert segundo.status_code == 201, segundo.text
    assert await _estoque(client, headers, variante) == 8


async def test_nuvemshop_com_pedido_externo_id_e_persistido_e_exposto(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=10)
    numero = _numero_externo()

    resp = await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=f"  {numero} "
    )

    assert resp.status_code == 201, resp.text
    criado = resp.json()
    assert criado["origem_canal"] == "NUVEMSHOP"
    assert criado["pedido_externo_id"] == numero  # espaços nas pontas removidos
    assert await _estoque(client, headers, variante) == 9

    detalhe = await client.get(f"/pedidos/{criado['id']}", headers=headers)
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["origem_canal"] == "NUVEMSHOP"
    assert detalhe.json()["pedido_externo_id"] == numero


async def test_forma_pagamento_nuvemshop_nao_amarra_origem_canal(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    """A UX de combinar forma de pagamento e canal é do frontend: a API aceita
    forma_pagamento NUVEMSHOP em pedido PDV/WHATSAPP e vice-versa."""
    variante = await _criar_variante(client, headers)

    resp = await client.post(
        "/pedidos",
        json={
            "itens": [{"variante_id": variante["id"], "quantidade": 1}],
            "pagamentos": [{"forma_pagamento": "NUVEMSHOP", "valor": "100.00"}],
            "origem_canal": "WHATSAPP",
        },
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["pagamentos"][0]["forma_pagamento"] == "NUVEMSHOP"


# ── validações (422) ──
async def test_nuvemshop_sem_pedido_externo_id_retorna_422_e_nao_baixa_estoque(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=5)

    resp = await _postar_pedido(client, headers, variante, origem_canal="NUVEMSHOP")

    assert resp.status_code == 422, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/erro-validacao"
    assert "pedido_externo_id" in resp.json()["detail"]
    assert await _estoque(client, headers, variante) == 5


async def test_whatsapp_com_pedido_externo_id_retorna_422_e_nao_baixa_estoque(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=5)

    resp = await _postar_pedido(
        client, headers, variante, origem_canal="WHATSAPP", pedido_externo_id="WA-1234"
    )

    assert resp.status_code == 422, resp.text
    problema = resp.json()
    assert problema["type"] == "https://amactive.dev/errors/erro-validacao"
    assert "WHATSAPP" in problema["detail"]
    assert "pedido_externo_id" in problema["detail"]
    assert await _estoque(client, headers, variante) == 5


async def test_pdv_com_pedido_externo_id_retorna_422_e_nao_baixa_estoque(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=5)

    resp = await _postar_pedido(
        client, headers, variante, origem_canal="PDV", pedido_externo_id="1234"
    )
    resp_implicito = await _postar_pedido(client, headers, variante, pedido_externo_id="1234")

    assert resp.status_code == 422, resp.text
    assert resp_implicito.status_code == 422, resp_implicito.text
    assert await _estoque(client, headers, variante) == 5


@pytest.mark.parametrize(
    "extras",
    [
        {"origem_canal": "INSTAGRAM"},
        {"origem_canal": "NUVEMSHOP", "pedido_externo_id": ""},
        {"origem_canal": "NUVEMSHOP", "pedido_externo_id": "   "},
        {"origem_canal": "NUVEMSHOP", "pedido_externo_id": "x" * 101},
    ],
)
async def test_valores_invalidos_de_canal_ou_numero_retornam_422(
    client: AsyncClient, headers: dict[str, str], extras: dict
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=5)

    resp = await _postar_pedido(client, headers, variante, **extras)

    assert resp.status_code == 422, resp.text
    assert await _estoque(client, headers, variante) == 5


# ── duplicidade ──
async def test_duplicidade_mesma_origem_e_numero_retorna_409_sem_baixar_estoque_de_novo(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=10)
    numero = _numero_externo()

    primeiro = await _postar_pedido(
        client, headers, variante, quantidade=2, origem_canal="NUVEMSHOP", pedido_externo_id=numero
    )
    assert primeiro.status_code == 201, primeiro.text
    assert await _estoque(client, headers, variante) == 8

    segundo = await _postar_pedido(
        client, headers, variante, quantidade=2, origem_canal="NUVEMSHOP", pedido_externo_id=numero
    )

    assert segundo.status_code == 409, segundo.text
    problema = segundo.json()
    assert problema["type"] == "https://amactive.dev/errors/conflito"
    assert numero in problema["detail"]
    assert "NUVEMSHOP" in problema["detail"]
    assert await _estoque(client, headers, variante) == 8  # baixou UMA vez só


async def test_duplicidade_ignora_espacos_nas_pontas_do_numero(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers)
    numero = _numero_externo()

    await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=numero
    )
    repetido = await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=f" {numero} "
    )

    assert repetido.status_code == 409, repetido.text


async def test_unicidade_do_numero_externo_vale_por_origem(
    client: AsyncClient, headers: dict[str, str], db_session: AsyncSession, usuario_teste
) -> None:
    """Pelo API só a NUVEMSHOP carrega número externo, então o escopo "por
    origem" (checagem prévia e índice único) é verificado direto no repositório
    e no banco: o mesmo número em OUTRA origem não conflita."""
    variante = await _criar_variante(client, headers)
    numero = _numero_externo()
    resp = await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=numero
    )
    assert resp.status_code == 201, resp.text
    usuario_id = usuario_teste.id

    repo = SqlAlchemyPedidoRepository(db_session)
    assert await repo.existe_pedido_externo(
        origem_canal=OrigemCanalPedido.NUVEMSHOP, pedido_externo_id=numero
    )
    assert not await repo.existe_pedido_externo(
        origem_canal=OrigemCanalPedido.WHATSAPP, pedido_externo_id=numero
    )
    assert not await repo.existe_pedido_externo(
        origem_canal=OrigemCanalPedido.PDV, pedido_externo_id=numero
    )
    assert not await repo.existe_pedido_externo(
        origem_canal=OrigemCanalPedido.NUVEMSHOP, pedido_externo_id=f"{numero}-outro"
    )
    # O índice único também aceita o mesmo número em outra origem.
    await _inserir_pedido_sql(
        db_session, usuario_id, f"UO-{uuid.uuid4().hex[:8]}", numero, "WHATSAPP"
    )


async def test_corrida_indice_unico_vira_409_e_nao_deixa_baixa_de_estoque(
    client: AsyncClient,
    headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defesa de corrida: a checagem prévia não enxerga o pedido concorrente
    (simulado forçando-a a responder "não existe"), então quem barra é o
    índice único parcial — que também vira 409, sem estoque baixado duas vezes."""
    variante = await _criar_variante(client, headers, estoque_inicial=10)
    numero = _numero_externo()
    primeiro = await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=numero
    )
    assert primeiro.status_code == 201, primeiro.text

    async def _nao_existe(self, *, origem_canal, pedido_externo_id) -> bool:
        return False

    monkeypatch.setattr(SqlAlchemyPedidoRepository, "existe_pedido_externo", _nao_existe)

    segundo = await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=numero
    )

    assert segundo.status_code == 409, segundo.text
    assert segundo.json()["type"] == "https://amactive.dev/errors/conflito"
    assert numero in segundo.json()["detail"]
    assert await _estoque(client, headers, variante) == 9  # só o primeiro pedido baixou

    # A sessão continua utilizável após o rollback do INSERT rejeitado.
    outro = await _postar_pedido(
        client, headers, variante, origem_canal="NUVEMSHOP", pedido_externo_id=_numero_externo()
    )
    assert outro.status_code == 201, outro.text
    assert await _estoque(client, headers, variante) == 8


async def _inserir_pedido_sql(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    numero: str,
    externo: str | None,
    origem: str = "NUVEMSHOP",
    cliente_id: uuid.UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO pedido (id, numero, cliente_id, usuario_id, status, subtotal, desconto,
                                valor_total, criado_em, origem_canal, pedido_externo_id)
            VALUES (:id, :numero, :cliente_id, :usuario_id, 'CONFIRMADO', 0, 0, 0, :agora,
                    CAST(:origem AS origem_canal_pedido), :externo)
            """
        ),
        {
            "id": uuid.uuid4(),
            "numero": numero,
            "cliente_id": cliente_id,
            "usuario_id": usuario_id,
            "agora": datetime.now(UTC),
            "origem": origem,
            "externo": externo,
        },
    )


async def test_violou_unicidade_distingue_indice_do_pedido_externo_de_outras_violacoes(
    db_session: AsyncSession, usuario_teste
) -> None:
    """Valida contra erros REAIS do asyncpg/Postgres (não fakes) a extração do
    nome da constraint usada para decidir entre 409 e propagar o erro."""
    # Lido antes de qualquer rollback: `rollback()` expira o ORM `usuario_teste`
    # e acessar `.id` depois disso tentaria I/O implícito (MissingGreenlet).
    usuario_id = usuario_teste.id

    async def _inserir(numero: str, externo: str | None, cliente_id: uuid.UUID | None) -> None:
        await _inserir_pedido_sql(db_session, usuario_id, numero, externo, "NUVEMSHOP", cliente_id)

    sufixo = uuid.uuid4().hex[:8]
    externo = _numero_externo()
    await _inserir(f"UQ-A-{sufixo}", externo, None)
    await db_session.commit()

    with pytest.raises(IntegrityError) as duplicado:
        await _inserir(f"UQ-B-{sufixo}", externo, None)
    assert violou_unicidade_pedido_externo(duplicado.value)
    await db_session.rollback()

    with pytest.raises(IntegrityError) as numero_duplicado:
        await _inserir(f"UQ-A-{sufixo}", None, None)
    assert not violou_unicidade_pedido_externo(numero_duplicado.value)
    await db_session.rollback()

    with pytest.raises(IntegrityError) as fk_invalida:
        await _inserir(f"UQ-C-{sufixo}", None, uuid.uuid4())
    assert not violou_unicidade_pedido_externo(fk_invalida.value)
    await db_session.rollback()


# ── listagem e relatório por canal ──
async def test_listagem_filtra_por_origem_canal(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=10)
    pdv = (await _postar_pedido(client, headers, variante)).json()
    whatsapp = (await _postar_pedido(client, headers, variante, origem_canal="WHATSAPP")).json()
    nuvemshop = (
        await _postar_pedido(
            client,
            headers,
            variante,
            origem_canal="NUVEMSHOP",
            pedido_externo_id=_numero_externo(),
        )
    ).json()

    async def _ids(**params: str) -> tuple[set[str], list[dict]]:
        resp = await client.get("/pedidos", params={"per_page": 100, **params}, headers=headers)
        assert resp.status_code == 200, resp.text
        corpo = resp.json()["data"]
        return {p["id"] for p in corpo}, corpo

    ids_whatsapp, itens_whatsapp = await _ids(origem_canal="WHATSAPP")
    assert whatsapp["id"] in ids_whatsapp
    assert pdv["id"] not in ids_whatsapp and nuvemshop["id"] not in ids_whatsapp
    assert {p["origem_canal"] for p in itens_whatsapp} == {"WHATSAPP"}

    ids_nuvemshop, itens_nuvemshop = await _ids(origem_canal="NUVEMSHOP")
    assert nuvemshop["id"] in ids_nuvemshop
    assert pdv["id"] not in ids_nuvemshop and whatsapp["id"] not in ids_nuvemshop
    assert {p["origem_canal"] for p in itens_nuvemshop} == {"NUVEMSHOP"}
    assert nuvemshop["pedido_externo_id"] in {p["pedido_externo_id"] for p in itens_nuvemshop}

    ids_pdv, itens_pdv = await _ids(origem_canal="PDV")
    assert pdv["id"] in ids_pdv
    assert whatsapp["id"] not in ids_pdv and nuvemshop["id"] not in ids_pdv
    assert {p["origem_canal"] for p in itens_pdv} == {"PDV"}

    # Sem filtro: todos os canais, e cada item traz os campos novos.
    ids_todos, itens_todos = await _ids()
    assert {pdv["id"], whatsapp["id"], nuvemshop["id"]} <= ids_todos
    assert all("origem_canal" in p and "pedido_externo_id" in p for p in itens_todos)


async def test_listagem_rejeita_origem_canal_invalida(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    resp = await client.get("/pedidos", params={"origem_canal": "INSTAGRAM"}, headers=headers)

    assert resp.status_code == 422, resp.text


async def _totais_relatorio(
    client: AsyncClient, headers: dict[str, str], **params: str
) -> tuple[int, Decimal]:
    hoje = datetime.now(UTC).date()
    resp = await client.get(
        "/relatorios/vendas-por-periodo",
        params={
            "data_inicio": (hoje - timedelta(days=1)).isoformat(),
            "data_fim": (hoje + timedelta(days=1)).isoformat(),
            **params,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    linhas = resp.json()["data"]
    return (
        sum(int(linha["total_pedidos"]) for linha in linhas),
        sum((Decimal(linha["faturamento"]) for linha in linhas), Decimal("0.00")),
    )


async def test_relatorio_vendas_por_periodo_filtra_por_origem_canal(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    variante = await _criar_variante(client, headers, estoque_inicial=10)
    antes = {
        canal: await _totais_relatorio(client, headers, **filtro)
        for canal, filtro in {
            "TODOS": {},
            "PDV": {"origem_canal": "PDV"},
            "WHATSAPP": {"origem_canal": "WHATSAPP"},
            "NUVEMSHOP": {"origem_canal": "NUVEMSHOP"},
        }.items()
    }

    assert (await _postar_pedido(client, headers, variante, quantidade=2)).status_code == 201
    assert (
        await _postar_pedido(client, headers, variante, quantidade=3, origem_canal="WHATSAPP")
    ).status_code == 201

    depois_todos = await _totais_relatorio(client, headers)
    depois_pdv = await _totais_relatorio(client, headers, origem_canal="PDV")
    depois_whatsapp = await _totais_relatorio(client, headers, origem_canal="WHATSAPP")
    depois_nuvemshop = await _totais_relatorio(client, headers, origem_canal="NUVEMSHOP")

    # Sem filtro: comportamento anterior (soma de todos os canais).
    assert depois_todos == (antes["TODOS"][0] + 2, antes["TODOS"][1] + Decimal("500.00"))
    assert depois_pdv == (antes["PDV"][0] + 1, antes["PDV"][1] + Decimal("200.00"))
    assert depois_whatsapp == (antes["WHATSAPP"][0] + 1, antes["WHATSAPP"][1] + Decimal("300.00"))
    assert depois_nuvemshop == antes["NUVEMSHOP"]


async def test_relatorio_rejeita_origem_canal_invalida(
    client: AsyncClient, headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/relatorios/vendas-por-periodo",
        params={"data_inicio": "2026-01-01", "data_fim": "2026-01-31", "origem_canal": "X"},
        headers=headers,
    )

    assert resp.status_code == 422, resp.text
