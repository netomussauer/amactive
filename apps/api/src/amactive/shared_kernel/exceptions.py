"""Exceções de domínio compartilhadas — base para o mapeamento RFC 7807.

Cada contexto define suas próprias exceções de domínio em
``<contexto>/domain/exceptions.py``, sempre herdando de uma destas classes
base. O handler global em ``main.py`` (``domain_error_handler``) captura
``DomainError`` e traduz para o formato ``ProblemDetails`` do
``docs/openapi.yaml`` §3.2, usando os atributos ``status_code``/``title``/
``type_slug`` de cada subclasse — nenhuma outra camada precisa saber como
montar a resposta HTTP de erro.
"""

from __future__ import annotations


class DomainError(Exception):
    """Erro de domínio genérico — nunca deve ser levantado diretamente,
    apenas suas subclasses especializadas."""

    status_code: int = 400
    type_slug: str = "erro"
    title: str = "Erro de domínio"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail

    def __str__(self) -> str:
        return self.detail


class EntidadeNaoEncontrada(DomainError):
    status_code = 404
    type_slug = "nao-encontrado"
    title = "Recurso não encontrado"


class ErroDeValidacao(DomainError):
    status_code = 422
    type_slug = "erro-validacao"
    title = "Dados de entrada inválidos"


class EstoqueInsuficiente(DomainError):
    status_code = 422
    type_slug = "estoque-insuficiente"
    title = "Estoque insuficiente"


class ConflitoDeEstado(DomainError):
    status_code = 409
    type_slug = "conflito"
    title = "Conflito de estado"


class NaoAutorizado(DomainError):
    status_code = 401
    type_slug = "nao-autorizado"
    title = "Não autorizado"


class ConflitoTransacional(DomainError):
    """Deadlock genuíno detectado pelo Postgres (SQLSTATE 40P01) mesmo após a
    aplicação seguir a disciplina de ordenação por `variante_id` — ver
    docs/data-model.md § Estratégia de Concorrência — Baixa de Estoque.
    Tratada internamente com um retry único; só chega ao cliente HTTP se o
    retry também falhar (rede de segurança, não o caminho comum)."""

    status_code = 503
    type_slug = "conflito-transacional"
    title = "Conflito temporário de concorrência — tente novamente"
