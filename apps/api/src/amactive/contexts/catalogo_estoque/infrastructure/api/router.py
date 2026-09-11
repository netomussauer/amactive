"""Controllers (FastAPI APIRouter) do contexto Catálogo & Estoque."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.application.use_cases.categoria_use_cases import (
    CriarCategoriaCommand,
    ListarCategoriasQuery,
)
from amactive.contexts.catalogo_estoque.application.use_cases.estoque_use_cases import (
    CriarMovimentacaoCommand,
    ListarAlertasEstoqueQuery,
    ListarEstoqueQuery,
    ListarMovimentacoesQuery,
)
from amactive.contexts.catalogo_estoque.application.use_cases.imagem_use_cases import (
    AtualizarOrdemImagemCommand,
    DefinirImagemPrincipalCommand,
    ListarImagensDoProdutoQuery,
    RemoverImagemCommand,
    UploadImagemCommand,
)
from amactive.contexts.catalogo_estoque.application.use_cases.produto_use_cases import (
    AtualizarProdutoCommand,
    CriarProdutoCommand,
    InativarProdutoCommand,
    ListarProdutosQuery,
    ObterProdutoQuery,
)
from amactive.contexts.catalogo_estoque.application.use_cases.variante_use_cases import (
    AtualizarVarianteCommand,
    CriarVarianteCommand,
    InativarVarianteCommand,
    ListarVariantesDoProdutoQuery,
    ObterVarianteQuery,
)
from amactive.contexts.catalogo_estoque.domain.entities import (
    Estoque,
    MotivoMovimentacao,
    MovimentacaoEstoque,
    Produto,
    ProdutoImagem,
    ProdutoVariante,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.infrastructure.api.schemas import (
    AtualizarOrdemImagemRequest,
    AtualizarProdutoRequest,
    AtualizarVarianteRequest,
    CategoriaListResponse,
    CategoriaResponse,
    CriarCategoriaRequest,
    CriarMovimentacaoRequest,
    CriarProdutoRequest,
    CriarVarianteRequest,
    EstoqueAlertaListResponse,
    EstoqueListResponse,
    EstoqueResponse,
    ImagemListResponse,
    ImagemResponse,
    MovimentacaoListResponse,
    MovimentacaoResponse,
    ProdutoDetalheResponse,
    ProdutoListResponse,
    ProdutoResponse,
    VarianteListResponse,
    VarianteResponse,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyCategoriaRepository,
    SqlAlchemyEstoqueRepository,
    SqlAlchemyImagemRepository,
    SqlAlchemyMovimentacaoRepository,
    SqlAlchemyProdutoRepository,
    SqlAlchemyVarianteRepository,
)
from amactive.contexts.catalogo_estoque.infrastructure.storage import (
    LocalDiskArmazenamentoDeImagem,
)
from amactive.core.security import CurrentUser, get_current_user
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.money import aplicar_desconto_percentual, parse_money, to_money_str
from amactive.shared_kernel.schemas import Pagination

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Categorias ──
@router.get("/categorias", tags=["Categorias"], response_model=CategoriaListResponse)
async def listar_categorias(
    session: AsyncSession = Depends(get_db_session),
) -> CategoriaListResponse:
    categorias = await ListarCategoriasQuery(SqlAlchemyCategoriaRepository(session)).executar()
    return CategoriaListResponse(data=[_categoria_response(c) for c in categorias])


@router.post(
    "/categorias",
    tags=["Categorias"],
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_categoria(
    payload: CriarCategoriaRequest, session: AsyncSession = Depends(get_db_session)
) -> CategoriaResponse:
    categoria = await CriarCategoriaCommand(SqlAlchemyCategoriaRepository(session)).executar(
        nome=payload.nome
    )
    await session.commit()
    return _categoria_response(categoria)


# ── Produtos ──
@router.get("/produtos", tags=["Produtos"], response_model=ProdutoListResponse)
async def listar_produtos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    busca: str | None = None,
    categoria_id: UUID | None = None,
    ativo: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ProdutoListResponse:
    produtos, total = await ListarProdutosQuery(SqlAlchemyProdutoRepository(session)).executar(
        page=page, per_page=per_page, busca=busca, categoria_id=categoria_id, ativo=ativo
    )
    return ProdutoListResponse(
        data=[_produto_response(p) for p in produtos],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.post(
    "/produtos",
    tags=["Produtos"],
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_produto(
    payload: CriarProdutoRequest, session: AsyncSession = Depends(get_db_session)
) -> ProdutoResponse:
    produto = await CriarProdutoCommand(SqlAlchemyProdutoRepository(session)).executar(
        nome=payload.nome,
        descricao=payload.descricao,
        categoria_id=payload.categoria_id,
        marca=payload.marca,
        desconto_percentual=payload.desconto_percentual,
    )
    await session.commit()
    return _produto_response(produto)


@router.get("/produtos/{produto_id}", tags=["Produtos"], response_model=ProdutoDetalheResponse)
async def obter_produto(
    produto_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> ProdutoDetalheResponse:
    produto = await ObterProdutoQuery(SqlAlchemyProdutoRepository(session)).executar(produto_id)
    variantes = await ListarVariantesDoProdutoQuery(SqlAlchemyVarianteRepository(session)).executar(
        produto_id
    )
    estoque_repo = SqlAlchemyEstoqueRepository(session)
    variantes_response = [
        await _variante_response(v, estoque_repo, produto.desconto_percentual) for v in variantes
    ]
    return ProdutoDetalheResponse(
        **_produto_response(produto).model_dump(), variantes=variantes_response
    )


@router.put("/produtos/{produto_id}", tags=["Produtos"], response_model=ProdutoResponse)
async def atualizar_produto(
    produto_id: UUID,
    payload: AtualizarProdutoRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ProdutoResponse:
    produto = await AtualizarProdutoCommand(SqlAlchemyProdutoRepository(session)).executar(
        produto_id,
        nome=payload.nome,
        descricao=payload.descricao,
        categoria_id=payload.categoria_id,
        marca=payload.marca,
        desconto_percentual=payload.desconto_percentual,
        ativo=payload.ativo,
    )
    await session.commit()
    return _produto_response(produto)


@router.delete("/produtos/{produto_id}", tags=["Produtos"], status_code=status.HTTP_204_NO_CONTENT)
async def inativar_produto(
    produto_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> None:
    await InativarProdutoCommand(SqlAlchemyProdutoRepository(session)).executar(produto_id)
    await session.commit()


# ── Variantes ──
@router.get(
    "/produtos/{produto_id}/variantes", tags=["Variantes"], response_model=VarianteListResponse
)
async def listar_variantes_do_produto(
    produto_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> VarianteListResponse:
    produto = await ObterProdutoQuery(SqlAlchemyProdutoRepository(session)).executar(produto_id)
    variantes = await ListarVariantesDoProdutoQuery(SqlAlchemyVarianteRepository(session)).executar(
        produto_id
    )
    estoque_repo = SqlAlchemyEstoqueRepository(session)
    return VarianteListResponse(
        data=[
            await _variante_response(v, estoque_repo, produto.desconto_percentual)
            for v in variantes
        ]
    )


@router.post(
    "/produtos/{produto_id}/variantes",
    tags=["Variantes"],
    response_model=VarianteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_variante(
    produto_id: UUID,
    payload: CriarVarianteRequest,
    session: AsyncSession = Depends(get_db_session),
    usuario: CurrentUser = Depends(get_current_user),
) -> VarianteResponse:
    # Garante que o produto exista (404 antes de tentar criar a variante).
    produto = await ObterProdutoQuery(SqlAlchemyProdutoRepository(session)).executar(produto_id)

    variante_repo = SqlAlchemyVarianteRepository(session)
    movimentacao_repo = SqlAlchemyMovimentacaoRepository(session)
    variante = await CriarVarianteCommand(variante_repo, movimentacao_repo).executar(
        produto_id=produto_id,
        sku=payload.sku,
        tamanho=payload.tamanho,
        cor=payload.cor,
        preco_venda=parse_money(payload.preco_venda),
        preco_custo=parse_money(payload.preco_custo) if payload.preco_custo else None,
        estoque_inicial=payload.estoque_inicial,
        usuario_id=usuario.id,
    )
    await session.commit()
    return await _variante_response(
        variante, SqlAlchemyEstoqueRepository(session), produto.desconto_percentual
    )


@router.get("/variantes/{variante_id}", tags=["Variantes"], response_model=VarianteResponse)
async def obter_variante(
    variante_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> VarianteResponse:
    variante = await ObterVarianteQuery(SqlAlchemyVarianteRepository(session)).executar(variante_id)
    produto = await ObterProdutoQuery(SqlAlchemyProdutoRepository(session)).executar(
        variante.produto_id
    )
    return await _variante_response(
        variante, SqlAlchemyEstoqueRepository(session), produto.desconto_percentual
    )


@router.put("/variantes/{variante_id}", tags=["Variantes"], response_model=VarianteResponse)
async def atualizar_variante(
    variante_id: UUID,
    payload: AtualizarVarianteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VarianteResponse:
    campos: dict[str, object] = {"cor": payload.cor, "ativo": payload.ativo}
    if payload.preco_venda is not None:
        campos["preco_venda"] = parse_money(payload.preco_venda)
    if payload.preco_custo is not None:
        campos["preco_custo"] = parse_money(payload.preco_custo)
    variante = await AtualizarVarianteCommand(SqlAlchemyVarianteRepository(session)).executar(
        variante_id, **campos
    )
    produto = await ObterProdutoQuery(SqlAlchemyProdutoRepository(session)).executar(
        variante.produto_id
    )
    await session.commit()
    return await _variante_response(
        variante, SqlAlchemyEstoqueRepository(session), produto.desconto_percentual
    )


@router.delete(
    "/variantes/{variante_id}", tags=["Variantes"], status_code=status.HTTP_204_NO_CONTENT
)
async def inativar_variante(
    variante_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> None:
    await InativarVarianteCommand(SqlAlchemyVarianteRepository(session)).executar(variante_id)
    await session.commit()


# ── Imagens ──
@router.post(
    "/produtos/{produto_id}/imagens",
    tags=["Imagens"],
    response_model=ImagemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_imagem(
    produto_id: UUID,
    cor: str = Form(..., max_length=50),
    arquivo: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> ImagemResponse:
    # Garante que o produto exista (404 antes de validar cor/arquivo).
    await ObterProdutoQuery(SqlAlchemyProdutoRepository(session)).executar(produto_id)

    conteudo = await arquivo.read()
    imagem = await UploadImagemCommand(
        SqlAlchemyVarianteRepository(session),
        SqlAlchemyImagemRepository(session),
        LocalDiskArmazenamentoDeImagem(),
    ).executar(produto_id=produto_id, cor=cor, content_type=arquivo.content_type, conteudo=conteudo)
    await session.commit()
    return _imagem_response(imagem)


@router.get("/produtos/{produto_id}/imagens", tags=["Imagens"], response_model=ImagemListResponse)
async def listar_imagens_do_produto(
    produto_id: UUID,
    cor: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ImagemListResponse:
    imagens = await ListarImagensDoProdutoQuery(SqlAlchemyImagemRepository(session)).executar(
        produto_id, cor=cor
    )
    return ImagemListResponse(data=[_imagem_response(i) for i in imagens])


@router.patch(
    "/produtos/{produto_id}/imagens/{imagem_id}/principal",
    tags=["Imagens"],
    response_model=ImagemResponse,
)
async def definir_imagem_principal(
    produto_id: UUID, imagem_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> ImagemResponse:
    imagem = await DefinirImagemPrincipalCommand(SqlAlchemyImagemRepository(session)).executar(
        produto_id, imagem_id
    )
    await session.commit()
    return _imagem_response(imagem)


@router.patch(
    "/produtos/{produto_id}/imagens/{imagem_id}", tags=["Imagens"], response_model=ImagemResponse
)
async def atualizar_ordem_imagem(
    produto_id: UUID,
    imagem_id: UUID,
    payload: AtualizarOrdemImagemRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ImagemResponse:
    imagem = await AtualizarOrdemImagemCommand(SqlAlchemyImagemRepository(session)).executar(
        produto_id, imagem_id, ordem=payload.ordem
    )
    await session.commit()
    return _imagem_response(imagem)


@router.delete(
    "/produtos/{produto_id}/imagens/{imagem_id}",
    tags=["Imagens"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remover_imagem(
    produto_id: UUID, imagem_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> None:
    await RemoverImagemCommand(
        SqlAlchemyImagemRepository(session), LocalDiskArmazenamentoDeImagem()
    ).executar(produto_id, imagem_id)
    await session.commit()


# ── Estoque ──
@router.get("/estoque", tags=["Estoque"], response_model=EstoqueListResponse)
async def listar_estoque(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sku: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> EstoqueListResponse:
    estoques, total = await ListarEstoqueQuery(SqlAlchemyEstoqueRepository(session)).executar(
        page=page, per_page=per_page, sku=sku
    )
    return EstoqueListResponse(
        data=[_estoque_response(e) for e in estoques],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.get("/estoque/alertas", tags=["Estoque"], response_model=EstoqueAlertaListResponse)
async def listar_alertas_estoque(
    session: AsyncSession = Depends(get_db_session),
) -> EstoqueAlertaListResponse:
    estoques = await ListarAlertasEstoqueQuery(SqlAlchemyEstoqueRepository(session)).executar()
    return EstoqueAlertaListResponse(data=[_estoque_response(e) for e in estoques])


@router.get("/estoque/movimentacoes", tags=["Estoque"], response_model=MovimentacaoListResponse)
async def listar_movimentacoes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    variante_id: UUID | None = None,
    tipo: TipoMovimentacao | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> MovimentacaoListResponse:
    movimentacoes, total = await ListarMovimentacoesQuery(
        SqlAlchemyMovimentacaoRepository(session)
    ).executar(page=page, per_page=per_page, variante_id=variante_id, tipo=tipo)
    return MovimentacaoListResponse(
        data=[_movimentacao_response(m) for m in movimentacoes],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.post(
    "/estoque/movimentacoes",
    tags=["Estoque"],
    response_model=MovimentacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_movimentacao(
    payload: CriarMovimentacaoRequest,
    session: AsyncSession = Depends(get_db_session),
    usuario: CurrentUser = Depends(get_current_user),
) -> MovimentacaoResponse:
    variante_repo = SqlAlchemyVarianteRepository(session)
    movimentacao_repo = SqlAlchemyMovimentacaoRepository(session)
    movimentacao = await CriarMovimentacaoCommand(variante_repo, movimentacao_repo).executar(
        variante_id=payload.variante_id,
        tipo=TipoMovimentacao(payload.tipo),
        quantidade=payload.quantidade,
        motivo=MotivoMovimentacao(payload.motivo),
        fornecedor_id=payload.fornecedor_id,
        usuario_id=usuario.id,
    )
    await session.commit()
    return _movimentacao_response(movimentacao)


# ── Mapeamento entidade -> schema HTTP ──
def _categoria_response(categoria) -> CategoriaResponse:
    return CategoriaResponse(
        id=categoria.id, nome=categoria.nome, slug=categoria.slug, ativo=categoria.ativo
    )


def _produto_response(produto: Produto) -> ProdutoResponse:
    return ProdutoResponse(
        id=produto.id,
        nome=produto.nome,
        descricao=produto.descricao,
        categoria_id=produto.categoria_id,
        marca=produto.marca,
        desconto_percentual=produto.desconto_percentual,
        ativo=produto.ativo,
        criado_em=produto.criado_em,
    )


async def _variante_response(
    variante: ProdutoVariante,
    estoque_repo: SqlAlchemyEstoqueRepository,
    desconto_percentual: Decimal | None = None,
) -> VarianteResponse:
    estoque = await estoque_repo.buscar_por_variante(variante.id)
    preco_promocional = (
        to_money_str(aplicar_desconto_percentual(variante.preco_venda, desconto_percentual))
        if desconto_percentual is not None
        else None
    )
    return VarianteResponse(
        id=variante.id,
        produto_id=variante.produto_id,
        sku=variante.sku,
        tamanho=variante.tamanho,
        cor=variante.cor,
        preco_venda=to_money_str(variante.preco_venda),
        preco_custo=to_money_str(variante.preco_custo)
        if variante.preco_custo is not None
        else None,
        ativo=variante.ativo,
        quantidade_estoque=estoque.quantidade if estoque else 0,
        desconto_percentual=to_money_str(desconto_percentual)
        if desconto_percentual is not None
        else None,
        preco_promocional=preco_promocional,
    )


def _imagem_response(imagem: ProdutoImagem) -> ImagemResponse:
    return ImagemResponse(
        id=imagem.id,
        produto_id=imagem.produto_id,
        cor=imagem.cor,
        url=imagem.url,
        ordem=imagem.ordem,
        principal=imagem.principal,
        criado_em=imagem.criado_em,
    )


def _estoque_response(estoque: Estoque) -> EstoqueResponse:
    return EstoqueResponse(
        variante_id=estoque.variante_id,
        sku=estoque.sku,
        produto_nome=estoque.produto_nome,
        quantidade=estoque.quantidade,
        estoque_minimo=estoque.estoque_minimo,
        em_alerta=estoque.em_alerta,
    )


def _movimentacao_response(movimentacao: MovimentacaoEstoque) -> MovimentacaoResponse:
    return MovimentacaoResponse(
        id=movimentacao.id,
        variante_id=movimentacao.variante_id,
        sku=movimentacao.sku,
        tipo=movimentacao.tipo.value,
        quantidade=movimentacao.quantidade,
        motivo=movimentacao.motivo.value,
        pedido_id=movimentacao.pedido_id,
        fornecedor_id=movimentacao.fornecedor_id,
        usuario_id=movimentacao.usuario_id,
        criado_em=movimentacao.criado_em,
    )
