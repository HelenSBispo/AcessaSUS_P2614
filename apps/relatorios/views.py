import logging
import time

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.auditorias.models import NaoConformidade
from apps.auditorias.views import _auditoria_visivel
from apps.contas.perfis import PermissaoMixin, negar, possui_permissao
from apps.normas.models import CriterioNormativo

from .geracao import gerar_html, gerar_pdf
from .models import Relatorio

logger = logging.getLogger("acessasus.relatorios")


class ConsultaView(PermissaoMixin, View):
    """Não conformidades ordenadas por severidade, com filtros (UC-04)."""

    acao_requerida = "auditoria.consultar"

    def get(self, request, pk):
        auditoria = _auditoria_visivel(request, pk)
        filtros = {k: request.GET.get(k, "") for k in ("severidade", "pagina", "principio")}
        apontamentos = auditoria.listar_apontamentos_por_severidade(filtros)
        return render(
            request,
            "relatorios/consulta.html",
            {
                "auditoria": auditoria,
                "apontamentos": apontamentos,
                "filtros": filtros,
                "niveis": NaoConformidade.NIVEIS,
                "principios": CriterioNormativo.PRINCIPIOS,
                "paginas": auditoria.paginas.all(),
                "pode_exportar": auditoria.concluida and possui_permissao(request.user, "relatorio.exportar"),
                "pendencias": [] if auditoria.concluida else auditoria.verificar_pendencias(),
            },
        )


class ExportarView(PermissaoMixin, View):
    """Exportação em PDF ou HTML somente de auditoria concluída (UC-05, RN06)."""

    acao_requerida = "relatorio.exportar"

    def post(self, request, pk, formato):
        auditoria = _auditoria_visivel(request, pk)
        formato = formato.upper()
        if formato not in dict(Relatorio.FORMATOS):
            negar(request.user, "relatorio.exportar")
        if not auditoria.concluida:
            messages.error(request, "A exportação só é permitida para auditorias concluídas (RN06).")
            return redirect("relatorios:consulta", pk=auditoria.pk)
        inicio = time.perf_counter()
        try:
            html = gerar_html(auditoria, request)
            if formato == Relatorio.PDF:
                conteudo, tipo = gerar_pdf(html, request.build_absolute_uri("/")), "application/pdf"
            else:
                conteudo, tipo = html.encode("utf-8"), "text/html; charset=utf-8"
        except Exception:
            logger.exception("falha ao gerar relatorio auditoria=%s formato=%s", auditoria.pk, formato)
            messages.error(request, "Não foi possível gerar o relatório. Nenhuma emissão foi registrada.")
            return redirect("relatorios:consulta", pk=auditoria.pk)
        duracao = int((time.perf_counter() - inicio) * 1000)
        Relatorio.objects.create(auditoria=auditoria, formato=formato, gerado_por=request.user, duracao_ms=duracao)
        logger.info("relatorio gerado auditoria=%s formato=%s duracao_ms=%s", auditoria.pk, formato, duracao)
        resposta = HttpResponse(conteudo, content_type=tipo)
        resposta["Content-Disposition"] = f'attachment; filename="acessasus-auditoria-{auditoria.pk}.{formato.lower()}"'
        return resposta
