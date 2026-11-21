"""Geração do relatório a partir de um único template HTML (ADR-05)."""

from __future__ import annotations

from django.template.loader import render_to_string
from django.utils import timezone


def contexto_relatorio(auditoria) -> dict:
    apontamentos = list(auditoria.listar_apontamentos_por_severidade())
    resultados = list(auditoria.obter_resultados().order_by("pagina_id", "criterio__codigo"))
    return {
        "auditoria": auditoria,
        "apontamentos": apontamentos,
        "resultados": resultados,
        "gerado_em": timezone.localtime(),
        "contagem": {n: sum(1 for a in apontamentos if a.nao_conformidade.nivel_severidade == n) for n in ("ALTA", "MEDIA", "BAIXA")},
    }


def gerar_html(auditoria, request=None) -> str:
    return render_to_string("relatorios/documento.html", contexto_relatorio(auditoria), request=request)


def gerar_pdf(html: str, base_url: str) -> bytes:
    from weasyprint import HTML  # import tardio: dependência de sistema (Pango)

    return HTML(string=html, base_url=base_url).write_pdf()
