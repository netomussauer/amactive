from __future__ import annotations

from amactive.shared_kernel.exceptions import NaoAutorizado


class CredenciaisInvalidas(NaoAutorizado):
    """Levantada quando e-mail/senha não conferem (ou usuário inativo) no login."""
