from __future__ import annotations

from amactive.shared_kernel.exceptions import ConflitoDeEstado, EntidadeNaoEncontrada


class ClienteNaoEncontrado(EntidadeNaoEncontrada):
    pass


class FornecedorNaoEncontrado(EntidadeNaoEncontrada):
    pass


class DocumentoDuplicado(ConflitoDeEstado):
    """CPF/CNPJ já cadastrado para outro cliente/fornecedor."""
