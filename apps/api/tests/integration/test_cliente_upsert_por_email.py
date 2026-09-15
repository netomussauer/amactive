"""Testes de integração de `ClienteRepository.upsert_por_email` — regra de
`ON CONFLICT (email) DO UPDATE` usada pela integração Nuvemshop (ver
docs/design-integracao-nuvemshop.md §3.3): `origem_cadastro` nunca é
sobrescrito e `cliente_externo_id` só é preenchido via `COALESCE` quando
ainda está vazio; os demais campos são sempre atualizados."""

from __future__ import annotations

import pytest

from amactive.contexts.cadastros.domain.entities import OrigemCadastroCliente
from amactive.contexts.cadastros.infrastructure.persistence.repositories import (
    SqlAlchemyClienteRepository,
)

pytestmark = pytest.mark.integration


async def test_upsert_por_email_cria_cliente_novo_com_origem_e_externo_id(db_session) -> None:
    repo = SqlAlchemyClienteRepository(db_session)

    cliente = await repo.upsert_por_email(
        email="nova.cliente@example.com",
        nome="Cliente Nuvemshop",
        cpf_cnpj=None,
        telefone="11999990000",
        endereco_logradouro="Rua das Flores, 10",
        endereco_cidade="São Paulo",
        endereco_uf="SP",
        endereco_cep="01000-000",
        cliente_externo_id="ns-cliente-1",
        origem_cadastro=OrigemCadastroCliente.NUVEMSHOP,
    )

    assert cliente.nome == "Cliente Nuvemshop"
    assert cliente.email == "nova.cliente@example.com"
    assert cliente.cliente_externo_id == "ns-cliente-1"
    assert cliente.origem_cadastro == OrigemCadastroCliente.NUVEMSHOP
    assert cliente.ativo is True


async def test_upsert_por_email_existente_preserva_origem_e_externo_id_ja_gravados(
    db_session,
) -> None:
    repo = SqlAlchemyClienteRepository(db_session)

    # Cliente nasceu manualmente no PDV — origem_cadastro=MANUAL (default do
    # banco) e sem cliente_externo_id.
    original = await repo.criar(
        nome="Cliente PDV",
        cpf_cnpj=None,
        email="cliente.pdv@example.com",
        telefone="11888880000",
        endereco_logradouro=None,
        endereco_cidade=None,
        endereco_uf=None,
        endereco_cep=None,
    )
    assert original.origem_cadastro == OrigemCadastroCliente.MANUAL
    assert original.cliente_externo_id is None

    # A mesma pessoa compra pela Nuvemshop usando o mesmo e-mail.
    atualizado = await repo.upsert_por_email(
        email="cliente.pdv@example.com",
        nome="Cliente PDV Atualizado",
        cpf_cnpj=None,
        telefone="11777770000",
        endereco_logradouro="Av. Central, 500",
        endereco_cidade="Campinas",
        endereco_uf="SP",
        endereco_cep="13000-000",
        cliente_externo_id="ns-cliente-2",
        origem_cadastro=OrigemCadastroCliente.NUVEMSHOP,
    )

    assert atualizado.id == original.id
    # origem_cadastro reflete como o registro nasceu — nunca é sobrescrito.
    assert atualizado.origem_cadastro == OrigemCadastroCliente.MANUAL
    # cliente_externo_id estava vazio — passa a ser gravado (COALESCE).
    assert atualizado.cliente_externo_id == "ns-cliente-2"
    # Demais campos sempre são atualizados (dados mais recentes do pedido).
    assert atualizado.nome == "Cliente PDV Atualizado"
    assert atualizado.telefone == "11777770000"
    assert atualizado.endereco_cidade == "Campinas"


async def test_upsert_por_email_nunca_substitui_cliente_externo_id_ja_gravado(db_session) -> None:
    repo = SqlAlchemyClienteRepository(db_session)

    primeiro = await repo.upsert_por_email(
        email="duplo.pedido@example.com",
        nome="Cliente Recorrente",
        cpf_cnpj=None,
        telefone="11666660000",
        endereco_logradouro=None,
        endereco_cidade=None,
        endereco_uf=None,
        endereco_cep=None,
        cliente_externo_id="ns-original",
        origem_cadastro=OrigemCadastroCliente.NUVEMSHOP,
    )
    assert primeiro.cliente_externo_id == "ns-original"

    segundo = await repo.upsert_por_email(
        email="duplo.pedido@example.com",
        nome="Cliente Recorrente",
        cpf_cnpj=None,
        telefone="11666660000",
        endereco_logradouro=None,
        endereco_cidade=None,
        endereco_uf=None,
        endereco_cep=None,
        # customer_id diferente não deveria acontecer na Nuvemshop, mas o
        # upsert não deve corromper o registro se acontecer.
        cliente_externo_id="ns-diferente",
        origem_cadastro=OrigemCadastroCliente.NUVEMSHOP,
    )

    assert segundo.id == primeiro.id
    assert segundo.cliente_externo_id == "ns-original"
