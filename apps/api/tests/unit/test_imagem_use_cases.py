"""Testes unitários de `UploadImagemCommand` e das demais operações de
imagem de produto — regras de negócio puras, com fakes em memória para
`VarianteRepository`/`ImagemRepository`/`ArmazenamentoDeImagemPort` (sem
banco/disco real — ver tests/integration/test_upload_imagem.py para o fluxo
completo contra Postgres + disco)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from amactive.contexts.catalogo_estoque.application.use_cases.imagem_use_cases import (
    TAMANHO_MAXIMO_BYTES,
    AtualizarOrdemImagemCommand,
    DefinirImagemPrincipalCommand,
    RemoverImagemCommand,
    UploadImagemCommand,
)
from amactive.contexts.catalogo_estoque.domain.entities import ProdutoImagem, ProdutoVariante
from amactive.contexts.catalogo_estoque.domain.exceptions import (
    ArquivoMuitoGrande,
    CorInvalidaParaProduto,
    ImagemNaoEncontrada,
    TipoDeArquivoInvalido,
)

pytestmark = pytest.mark.unit

_PNG_CONTENT_TYPE = "image/png"


def _variante(*, produto_id: UUID, cor: str, ativo: bool = True) -> ProdutoVariante:
    return ProdutoVariante(
        id=uuid4(),
        produto_id=produto_id,
        sku=f"SKU-{uuid4().hex[:6]}",
        tamanho="M",
        cor=cor,
        preco_venda=Decimal("99.90"),
        preco_custo=None,
        ativo=ativo,
    )


@dataclass
class _VarianteRepositoryFake:
    variantes: list[ProdutoVariante]

    async def listar_por_produto(self, produto_id: UUID) -> list[ProdutoVariante]:
        return [v for v in self.variantes if v.produto_id == produto_id]

    async def criar(self, **kwargs: object) -> ProdutoVariante:  # pragma: no cover - não usado
        raise NotImplementedError

    async def buscar_por_id(self, variante_id: UUID) -> ProdutoVariante | None:
        raise NotImplementedError  # pragma: no cover - não usado

    async def atualizar(self, variante_id: UUID, **campos: object) -> ProdutoVariante | None:
        raise NotImplementedError  # pragma: no cover - não usado

    async def inativar(self, variante_id: UUID) -> bool:
        raise NotImplementedError  # pragma: no cover - não usado


@dataclass
class _ImagemRepositoryFake:
    imagens: list[ProdutoImagem] = field(default_factory=list)
    falha_ao_criar: bool = False

    async def contar_por_produto_e_cor(self, produto_id: UUID, cor: str) -> int:
        return sum(1 for i in self.imagens if i.produto_id == produto_id and i.cor == cor)

    async def criar(
        self, *, produto_id: UUID, cor: str, url: str, ordem: int, principal: bool
    ) -> ProdutoImagem:
        if self.falha_ao_criar:
            raise RuntimeError("falha simulada ao persistir")
        imagem = ProdutoImagem(
            id=uuid4(),
            produto_id=produto_id,
            cor=cor,
            url=url,
            ordem=ordem,
            principal=principal,
            criado_em=datetime.now(UTC),
        )
        self.imagens.append(imagem)
        return imagem

    async def listar_por_produto(
        self, produto_id: UUID, *, cor: str | None = None
    ) -> list[ProdutoImagem]:
        raise NotImplementedError  # pragma: no cover - não usado

    async def buscar_por_id(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem | None:
        raise NotImplementedError  # pragma: no cover - não usado

    async def definir_principal(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem | None:
        for i, imagem in enumerate(self.imagens):
            if imagem.id == imagem_id and imagem.produto_id == produto_id:
                for j, outra in enumerate(self.imagens):
                    if outra.produto_id == produto_id and outra.cor == imagem.cor:
                        self.imagens[j] = ProdutoImagem(
                            id=outra.id,
                            produto_id=outra.produto_id,
                            cor=outra.cor,
                            url=outra.url,
                            ordem=outra.ordem,
                            principal=(outra.id == imagem_id),
                            criado_em=outra.criado_em,
                        )
                return self.imagens[i]
        return None

    async def atualizar_ordem(
        self, produto_id: UUID, imagem_id: UUID, *, ordem: int
    ) -> ProdutoImagem | None:
        for i, imagem in enumerate(self.imagens):
            if imagem.id == imagem_id and imagem.produto_id == produto_id:
                atualizada = ProdutoImagem(
                    id=imagem.id,
                    produto_id=imagem.produto_id,
                    cor=imagem.cor,
                    url=imagem.url,
                    ordem=ordem,
                    principal=imagem.principal,
                    criado_em=imagem.criado_em,
                )
                self.imagens[i] = atualizada
                return atualizada
        return None

    async def remover(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem | None:
        for i, imagem in enumerate(self.imagens):
            if imagem.id == imagem_id and imagem.produto_id == produto_id:
                return self.imagens.pop(i)
        return None


@dataclass
class _StorageFake:
    salvos: list[str] = field(default_factory=list)
    removidos: list[str] = field(default_factory=list)
    falha_ao_remover: bool = False

    async def salvar(self, *, produto_id: UUID, conteudo: bytes, extensao: str) -> str:
        url = f"/media/produtos/{produto_id}/{uuid4()}{extensao}"
        self.salvos.append(url)
        return url

    async def remover(self, url: str) -> None:
        if self.falha_ao_remover:
            raise OSError("arquivo não encontrado (simulado)")
        self.removidos.append(url)


def _comando(
    *, variantes: list[ProdutoVariante], imagens: _ImagemRepositoryFake, storage: _StorageFake
) -> UploadImagemCommand:
    return UploadImagemCommand(_VarianteRepositoryFake(variantes), imagens, storage)


async def test_cor_e_normalizada_para_o_valor_exato_da_variante() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Azul")
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()

    imagem = await _comando(variantes=[variante], imagens=imagens, storage=storage).executar(
        produto_id=produto_id, cor="azul", content_type=_PNG_CONTENT_TYPE, conteudo=b"conteudo"
    )

    assert imagem.cor == "Azul"


async def test_cor_sem_variante_correspondente_e_rejeitada() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Azul")
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()

    with pytest.raises(CorInvalidaParaProduto):
        await _comando(variantes=[variante], imagens=imagens, storage=storage).executar(
            produto_id=produto_id, cor="Verde", content_type=_PNG_CONTENT_TYPE, conteudo=b"x"
        )
    assert storage.salvos == []


async def test_cor_de_variante_inativa_e_rejeitada() -> None:
    produto_id = uuid4()
    variante_inativa = _variante(produto_id=produto_id, cor="Azul", ativo=False)
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()

    with pytest.raises(CorInvalidaParaProduto):
        await _comando(variantes=[variante_inativa], imagens=imagens, storage=storage).executar(
            produto_id=produto_id, cor="Azul", content_type=_PNG_CONTENT_TYPE, conteudo=b"x"
        )


async def test_primeira_imagem_da_cor_e_marcada_como_principal_automaticamente() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Preto")
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()

    imagem = await _comando(variantes=[variante], imagens=imagens, storage=storage).executar(
        produto_id=produto_id, cor="Preto", content_type=_PNG_CONTENT_TYPE, conteudo=b"x"
    )

    assert imagem.principal is True
    assert imagem.ordem == 0


async def test_segunda_imagem_da_mesma_cor_nao_e_principal_e_incrementa_ordem() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Preto")
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()
    comando = _comando(variantes=[variante], imagens=imagens, storage=storage)

    await comando.executar(
        produto_id=produto_id, cor="Preto", content_type=_PNG_CONTENT_TYPE, conteudo=b"x"
    )
    segunda = await comando.executar(
        produto_id=produto_id, cor="Preto", content_type=_PNG_CONTENT_TYPE, conteudo=b"y"
    )

    assert segunda.principal is False
    assert segunda.ordem == 1


async def test_tipo_de_arquivo_nao_suportado_e_rejeitado() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Preto")
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()

    with pytest.raises(TipoDeArquivoInvalido):
        await _comando(variantes=[variante], imagens=imagens, storage=storage).executar(
            produto_id=produto_id,
            cor="Preto",
            content_type="application/pdf",
            conteudo=b"%PDF-1.4",
        )
    assert storage.salvos == []


async def test_arquivo_maior_que_o_limite_e_rejeitado() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Preto")
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()
    conteudo_grande = b"0" * (TAMANHO_MAXIMO_BYTES + 1)

    with pytest.raises(ArquivoMuitoGrande):
        await _comando(variantes=[variante], imagens=imagens, storage=storage).executar(
            produto_id=produto_id,
            cor="Preto",
            content_type=_PNG_CONTENT_TYPE,
            conteudo=conteudo_grande,
        )
    assert storage.salvos == []


async def test_falha_ao_persistir_remove_arquivo_ja_salvo_em_disco() -> None:
    produto_id = uuid4()
    variante = _variante(produto_id=produto_id, cor="Preto")
    imagens = _ImagemRepositoryFake(falha_ao_criar=True)
    storage = _StorageFake()

    with pytest.raises(RuntimeError):
        await _comando(variantes=[variante], imagens=imagens, storage=storage).executar(
            produto_id=produto_id, cor="Preto", content_type=_PNG_CONTENT_TYPE, conteudo=b"x"
        )

    assert storage.salvos == storage.removidos


async def test_definir_principal_desmarca_a_anterior_da_mesma_cor() -> None:
    produto_id = uuid4()
    imagens = _ImagemRepositoryFake(
        imagens=[
            ProdutoImagem(
                id=uuid4(),
                produto_id=produto_id,
                cor="Preto",
                url="/media/1.png",
                ordem=0,
                principal=True,
                criado_em=datetime.now(UTC),
            ),
            ProdutoImagem(
                id=uuid4(),
                produto_id=produto_id,
                cor="Preto",
                url="/media/2.png",
                ordem=1,
                principal=False,
                criado_em=datetime.now(UTC),
            ),
        ]
    )
    segunda_id = imagens.imagens[1].id

    nova_principal = await DefinirImagemPrincipalCommand(imagens).executar(produto_id, segunda_id)

    assert nova_principal.principal is True
    principais = [i.principal for i in imagens.imagens]
    assert principais.count(True) == 1


async def test_definir_principal_de_imagem_inexistente_levanta_nao_encontrada() -> None:
    imagens = _ImagemRepositoryFake()

    with pytest.raises(ImagemNaoEncontrada):
        await DefinirImagemPrincipalCommand(imagens).executar(uuid4(), uuid4())


async def test_atualizar_ordem_de_imagem_inexistente_levanta_nao_encontrada() -> None:
    imagens = _ImagemRepositoryFake()

    with pytest.raises(ImagemNaoEncontrada):
        await AtualizarOrdemImagemCommand(imagens).executar(uuid4(), uuid4(), ordem=2)


async def test_remover_imagem_falha_na_remocao_fisica_nao_propaga_erro() -> None:
    produto_id = uuid4()
    imagem_id = uuid4()
    imagens = _ImagemRepositoryFake(
        imagens=[
            ProdutoImagem(
                id=imagem_id,
                produto_id=produto_id,
                cor="Preto",
                url="/media/1.png",
                ordem=0,
                principal=True,
                criado_em=datetime.now(UTC),
            )
        ]
    )
    storage = _StorageFake(falha_ao_remover=True)

    # Não deve levantar exceção: o registro em banco (fonte de verdade da
    # UI) já foi removido com sucesso mesmo que o arquivo físico não possa
    # ser removido (ex.: já apagado manualmente do volume).
    await RemoverImagemCommand(imagens, storage).executar(produto_id, imagem_id)

    assert imagens.imagens == []


async def test_remover_imagem_inexistente_levanta_nao_encontrada() -> None:
    imagens = _ImagemRepositoryFake()
    storage = _StorageFake()

    with pytest.raises(ImagemNaoEncontrada):
        await RemoverImagemCommand(imagens, storage).executar(uuid4(), uuid4())
