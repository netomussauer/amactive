"""Casos de uso de Imagem de Produto (galeria por cor) — Command/Query.

Ver docs/data-model.md decisão #13: `produto_imagem.cor` não é FK (não há
chave composta possível contra `produto_variante`), então a validação de que
a cor informada corresponde a uma variante ativa do produto é
responsabilidade desta camada, não do banco.
"""

from __future__ import annotations

from uuid import UUID

from amactive.contexts.catalogo_estoque.domain.entities import ProdutoImagem
from amactive.contexts.catalogo_estoque.domain.exceptions import (
    ArquivoMuitoGrande,
    CorInvalidaParaProduto,
    ImagemNaoEncontrada,
    TipoDeArquivoInvalido,
)
from amactive.contexts.catalogo_estoque.domain.repositories import (
    ArmazenamentoDeImagemPort,
    ImagemRepository,
    VarianteRepository,
)

# Tipos MIME aceitos, mapeados para a extensão de arquivo gravada em disco.
_TIPOS_ACEITOS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5MB


class UploadImagemCommand:
    """Valida e persiste uma nova imagem de produto.

    A `cor` informada é normalizada para o valor exato cadastrado na
    variante correspondente (comparação case-insensitive), evitando que
    grafias diferentes (`"Azul"` vs `"azul"`) fragmentem a galeria e a regra
    de "uma principal por cor" (índice único parcial em `produto_id, cor`).
    """

    def __init__(
        self,
        variante_repository: VarianteRepository,
        imagem_repository: ImagemRepository,
        storage: ArmazenamentoDeImagemPort,
    ) -> None:
        self._variantes = variante_repository
        self._imagens = imagem_repository
        self._storage = storage

    async def executar(
        self,
        *,
        produto_id: UUID,
        cor: str,
        content_type: str | None,
        conteudo: bytes,
    ) -> ProdutoImagem:
        cor_normalizada = await self._resolver_cor(produto_id=produto_id, cor=cor)
        extensao = self._validar_arquivo(content_type=content_type, conteudo=conteudo)

        url = await self._storage.salvar(
            produto_id=produto_id, conteudo=conteudo, extensao=extensao
        )
        try:
            ordem = await self._imagens.contar_por_produto_e_cor(produto_id, cor_normalizada)
            return await self._imagens.criar(
                produto_id=produto_id,
                cor=cor_normalizada,
                url=url,
                ordem=ordem,
                principal=ordem == 0,
            )
        except Exception:
            # O arquivo já foi gravado em disco — se o registro em banco
            # falhar por qualquer motivo, não deixamos um arquivo órfão
            # (sem registro correspondente, portanto invisível/inacessível
            # pela aplicação).
            await self._storage.remover(url)
            raise

    async def _resolver_cor(self, *, produto_id: UUID, cor: str) -> str:
        variantes = await self._variantes.listar_por_produto(produto_id)
        alvo = cor.strip().lower()
        for variante in variantes:
            if variante.ativo and variante.cor.strip().lower() == alvo:
                return variante.cor
        raise CorInvalidaParaProduto(
            f"Cor '{cor}' não corresponde a nenhuma variante ativa do produto {produto_id}."
        )

    @staticmethod
    def _validar_arquivo(*, content_type: str | None, conteudo: bytes) -> str:
        extensao = _TIPOS_ACEITOS.get(content_type or "")
        if extensao is None:
            aceitos = ", ".join(sorted(_TIPOS_ACEITOS))
            raise TipoDeArquivoInvalido(
                f"Tipo de arquivo '{content_type}' não suportado. Tipos aceitos: {aceitos}."
            )
        if len(conteudo) > TAMANHO_MAXIMO_BYTES:
            limite_mb = TAMANHO_MAXIMO_BYTES // (1024 * 1024)
            raise ArquivoMuitoGrande(f"Arquivo excede o tamanho máximo permitido de {limite_mb}MB.")
        return extensao


class ListarImagensDoProdutoQuery:
    def __init__(self, repository: ImagemRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID, *, cor: str | None = None) -> list[ProdutoImagem]:
        return await self._repository.listar_por_produto(produto_id, cor=cor)


class DefinirImagemPrincipalCommand:
    def __init__(self, repository: ImagemRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem:
        imagem = await self._repository.definir_principal(produto_id, imagem_id)
        if imagem is None:
            raise ImagemNaoEncontrada(
                f"Imagem {imagem_id} não encontrada para o produto {produto_id}."
            )
        return imagem


class AtualizarOrdemImagemCommand:
    def __init__(self, repository: ImagemRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID, imagem_id: UUID, *, ordem: int) -> ProdutoImagem:
        imagem = await self._repository.atualizar_ordem(produto_id, imagem_id, ordem=ordem)
        if imagem is None:
            raise ImagemNaoEncontrada(
                f"Imagem {imagem_id} não encontrada para o produto {produto_id}."
            )
        return imagem


class RemoverImagemCommand:
    """Remove o registro em banco (fonte de verdade para a UI) e, em
    seguida, o arquivo físico — falha ao remover o arquivo (ex.: já
    removido manualmente do volume) não desfaz nem reporta erro na remoção
    do registro, que já foi concluída com sucesso."""

    def __init__(self, repository: ImagemRepository, storage: ArmazenamentoDeImagemPort) -> None:
        self._repository = repository
        self._storage = storage

    async def executar(self, produto_id: UUID, imagem_id: UUID) -> None:
        imagem = await self._repository.remover(produto_id, imagem_id)
        if imagem is None:
            raise ImagemNaoEncontrada(
                f"Imagem {imagem_id} não encontrada para o produto {produto_id}."
            )
        try:
            await self._storage.remover(imagem.url)
        except OSError:
            pass
