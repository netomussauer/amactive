"""Adaptador de armazenamento físico de imagens de produto — implementa
`domain.repositories.ArmazenamentoDeImagemPort`.

Disco local via volume Docker nesta fase (ver docs/data-model.md decisão
#13 e docs/avaliacao-integracao-nuvemshop.md para a evolução futura a um
object storage). Os arquivos ficam em
`{settings.uploads_dir}/produtos/{produto_id}/{uuid}.{ext}` e são servidos
publicamente em `/media/produtos/{produto_id}/{uuid}.{ext}` via
`fastapi.staticfiles.StaticFiles` (ver main.py).
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from uuid import UUID

from amactive.core.config import settings

_MEDIA_URL_PREFIX = "/media"


class LocalDiskArmazenamentoDeImagem:
    """Implementação concreta de `ArmazenamentoDeImagemPort` para disco
    local. Lê `settings.uploads_dir` na construção (não em import time),
    para que overrides de settings (ex.: em testes) tenham efeito."""

    def __init__(self, uploads_dir: str | None = None) -> None:
        self._uploads_dir = Path(uploads_dir if uploads_dir is not None else settings.uploads_dir)

    async def salvar(self, *, produto_id: UUID, conteudo: bytes, extensao: str) -> str:
        nome_arquivo = f"{uuid.uuid4()}{extensao}"
        pasta = self._uploads_dir / "produtos" / str(produto_id)
        caminho = pasta / nome_arquivo
        await asyncio.to_thread(self._escrever, pasta, caminho, conteudo)
        return f"{_MEDIA_URL_PREFIX}/produtos/{produto_id}/{nome_arquivo}"

    async def remover(self, url: str) -> None:
        caminho = self._url_para_caminho(url)
        await asyncio.to_thread(self._remover_se_existir, caminho)

    def _url_para_caminho(self, url: str) -> Path:
        relativo = url.removeprefix(_MEDIA_URL_PREFIX).lstrip("/")
        return self._uploads_dir / relativo

    @staticmethod
    def _escrever(pasta: Path, caminho: Path, conteudo: bytes) -> None:
        pasta.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)

    @staticmethod
    def _remover_se_existir(caminho: Path) -> None:
        caminho.unlink(missing_ok=True)
