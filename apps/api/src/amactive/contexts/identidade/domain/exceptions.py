from __future__ import annotations

from amactive.shared_kernel.exceptions import ConflitoDeEstado, EntidadeNaoEncontrada, NaoAutorizado


class CredenciaisInvalidas(NaoAutorizado):
    """Levantada quando e-mail/senha não conferem (ou usuário inativo) no login."""


class UsuarioNaoEncontrado(EntidadeNaoEncontrada):
    pass


class EmailDuplicado(ConflitoDeEstado):
    """E-mail já cadastrado para outro usuário (`usuario.email` é UNIQUE)."""


class UltimoAdminAtivo(ConflitoDeEstado):
    """Levantada ao tentar desativar a própria conta ou rebaixar o próprio
    papel de ADMIN para outro quando o usuário é o único ADMIN ativo do
    sistema — salvaguarda para que o ADMIN nunca se tranque fora do sistema
    (ver docs/SDD.md ADR-007)."""
