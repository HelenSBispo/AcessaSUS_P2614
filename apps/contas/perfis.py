"""Perfis de acesso e matriz de permissões do MVP (RN05, RF006, ADR-04)."""

from __future__ import annotations

import logging

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

logger = logging.getLogger("acessasus.acesso")

AUDITOR = "Auditor"
GESTOR_TI = "Gestor de TI"
PERFIS = (AUDITOR, GESTOR_TI)

# Ação -> perfis com permissão. "próprias" é verificado nas views pelo dono da auditoria.
MATRIZ_PERMISSOES: dict[str, set[str]] = {
    "projeto.editar": {AUDITOR},
    "projeto.ver": {AUDITOR, GESTOR_TI},
    "auditoria.executar": {AUDITOR},
    "auditoria.consultar": {AUDITOR, GESTOR_TI},
    "relatorio.exportar": {AUDITOR, GESTOR_TI},
}


def perfil_de(usuario) -> str | None:
    if not getattr(usuario, "is_authenticated", False):
        return None
    nomes = set(usuario.groups.values_list("name", flat=True))
    for perfil in PERFIS:
        if perfil in nomes:
            return perfil
    return None


def possui_permissao(usuario, acao: str) -> bool:
    if getattr(usuario, "is_superuser", False):
        return True
    return perfil_de(usuario) in MATRIZ_PERMISSOES.get(acao, set())


def negar(usuario, acao: str):
    logger.warning("acesso negado usuario=%s acao=%s", getattr(usuario, "pk", None), acao)
    raise PermissionDenied


class PermissaoMixin(AccessMixin):
    """Exige login e a ação informada em `acao_requerida`."""

    acao_requerida: str = ""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not possui_permissao(request.user, self.acao_requerida):
            negar(request.user, self.acao_requerida)
        return super().dispatch(request, *args, **kwargs)


def pode_ver_auditoria(usuario, auditoria) -> bool:
    """Auditor vê apenas as próprias auditorias; Gestor de TI vê todas."""
    if getattr(usuario, "is_superuser", False):
        return True
    perfil = perfil_de(usuario)
    if perfil == GESTOR_TI:
        return True
    return perfil == AUDITOR and auditoria.auditor_id == usuario.pk
