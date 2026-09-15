"""Implementa `ClienteIntegracaoPort` (`domain/repositories.py`) chamando
exclusivamente `ClienteRepository.upsert_por_email` — ver
docs/design-integracao-nuvemshop.md §3.3.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.cadastros.domain.entities import OrigemCadastroCliente
from amactive.contexts.cadastros.infrastructure.persistence.repositories import (
    SqlAlchemyClienteRepository,
)
from amactive.contexts.integracao_canais.domain.repositories import EnderecoExterno


class CadastrosIntegracaoGateway:
    """Implementa `ClienteIntegracaoPort` — todo pedido/cliente importado da
    Nuvemshop nasce ou é atualizado com `origem_cadastro=NUVEMSHOP` (design
    §3.3); a regra de "nunca sobrescrever a origem/`cliente_externo_id` já
    gravados" vive inteiramente em `ClienteRepository.upsert_por_email`, não
    aqui."""

    def __init__(self, session: AsyncSession) -> None:
        self._clientes = SqlAlchemyClienteRepository(session)

    async def resolver_ou_criar_por_email(
        self,
        *,
        email: str,
        nome: str,
        cpf_cnpj: str | None,
        telefone: str | None,
        endereco: EnderecoExterno | None,
        cliente_externo_id: str,
    ) -> UUID:
        cliente = await self._clientes.upsert_por_email(
            email=email,
            nome=nome,
            cpf_cnpj=cpf_cnpj,
            telefone=telefone,
            endereco_logradouro=endereco.logradouro if endereco else None,
            endereco_cidade=endereco.cidade if endereco else None,
            endereco_uf=endereco.uf if endereco else None,
            endereco_cep=endereco.cep if endereco else None,
            cliente_externo_id=cliente_externo_id,
            origem_cadastro=OrigemCadastroCliente.NUVEMSHOP,
        )
        return cliente.id
