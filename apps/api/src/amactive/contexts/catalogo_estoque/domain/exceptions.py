from __future__ import annotations

from amactive.shared_kernel.exceptions import (
    ConflitoDeEstado,
    EntidadeNaoEncontrada,
    ErroDeValidacao,
    EstoqueInsuficiente,
    PayloadMuitoGrande,
)


class CategoriaNaoEncontrada(EntidadeNaoEncontrada):
    pass


class ProdutoNaoEncontrado(EntidadeNaoEncontrada):
    pass


class VarianteNaoEncontrada(EntidadeNaoEncontrada):
    pass


class SkuDuplicado(ConflitoDeEstado):
    pass


class DadosDeMovimentacaoInvalidos(ErroDeValidacao):
    pass


class SaldoDeEstoqueInsuficiente(EstoqueInsuficiente):
    """Tradução do erro do trigger `fn_aplicar_movimentacao_estoque` (SQLSTATE P0001)
    — ver docs/data-model.md § Estratégia de Concorrência — Baixa de Estoque."""


class ImagemNaoEncontrada(EntidadeNaoEncontrada):
    pass


class CorInvalidaParaProduto(ErroDeValidacao):
    """A `cor` informada no upload de uma imagem não corresponde a nenhuma
    variante ativa do produto — `produto_imagem.cor` não é FK (ver
    docs/data-model.md decisão #13), então esta validação é responsabilidade
    exclusiva da camada de aplicação."""


class TipoDeArquivoInvalido(ErroDeValidacao):
    pass


class ArquivoMuitoGrande(PayloadMuitoGrande):
    pass
