from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.contas.perfis import GESTOR_TI, PermissaoMixin, negar, perfil_de, pode_ver_auditoria
from apps.normas.models import CriterioNormativo
from apps.projetos.models import Projeto
from apps.severidade.regra import calcular_severidade

from .forms import AvaliacaoForm, NovaAuditoriaForm
from .models import Auditoria, NaoConformidade, ResultadoChecklist
from .servicos import concluir_auditoria, iniciar_auditoria, registrar_avaliacao

ROTULO_NIVEL = dict(NaoConformidade.NIVEIS)


class PainelView(LoginRequiredMixin, TemplateView):
    template_name = "auditorias/painel.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user
        auditorias = Auditoria.objects.select_related("projeto", "base").annotate(
            n_resultados=Count("resultados", distinct=True),
            n_alta=Count("resultados", filter=Q(resultados__nao_conformidade__nivel_severidade="ALTA"), distinct=True),
            n_media=Count("resultados", filter=Q(resultados__nao_conformidade__nivel_severidade="MEDIA"), distinct=True),
            n_baixa=Count("resultados", filter=Q(resultados__nao_conformidade__nivel_severidade="BAIXA"), distinct=True),
        )
        if perfil_de(usuario) != GESTOR_TI and not usuario.is_superuser:
            auditorias = auditorias.filter(auditor=usuario)
        auditorias = list(auditorias)
        for a in auditorias:
            a.n_esperado = a.total_esperado()
        ctx.update(
            auditorias=auditorias,
            n_projetos=Projeto.objects.count(),
            n_andamento=sum(1 for a in auditorias if not a.concluida),
            n_concluidas=sum(1 for a in auditorias if a.concluida),
            n_ncs=sum(a.n_alta + a.n_media + a.n_baixa for a in auditorias),
        )
        return ctx


class NovaAuditoriaView(PermissaoMixin, View):
    acao_requerida = "auditoria.executar"
    template_name = "auditorias/nova.html"

    def get(self, request):
        projeto = Projeto.objects.filter(pk=request.GET.get("projeto")).first() if request.GET.get("projeto") else None
        return render(request, self.template_name, {"form": NovaAuditoriaForm(projeto=projeto), "projeto": projeto})

    def post(self, request):
        form = NovaAuditoriaForm(request.POST)
        if form.is_valid():
            try:
                auditoria = iniciar_auditoria(
                    form.cleaned_data["projeto"], form.cleaned_data["paginas"], form.cleaned_data["base"], request.user
                )
            except ValidationError as erro:
                form.add_error(None, erro)
            else:
                messages.success(request, "Auditoria criada. Situação: Em andamento.")
                return redirect("auditorias:checklist", pk=auditoria.pk)
        return render(request, self.template_name, {"form": form, "projeto": None}, status=400)


def _auditoria_visivel(request, pk) -> Auditoria:
    auditoria = get_object_or_404(Auditoria.objects.select_related("projeto", "base", "auditor"), pk=pk)
    if not pode_ver_auditoria(request.user, auditoria):
        negar(request.user, "auditoria.consultar")
    return auditoria


def _auditoria_executavel(request, pk) -> Auditoria:
    auditoria = _auditoria_visivel(request, pk)
    if auditoria.auditor_id != request.user.pk:
        negar(request.user, "auditoria.executar")
    return auditoria


class ChecklistView(PermissaoMixin, View):
    """Checklist por página, agrupado por princípio (UC-02)."""

    acao_requerida = "auditoria.consultar"
    template_name = "auditorias/checklist.html"

    def get(self, request, pk):
        auditoria = _auditoria_visivel(request, pk)
        paginas = list(auditoria.paginas.all())
        pagina = next((p for p in paginas if str(p.pk) == request.GET.get("pagina")), paginas[0] if paginas else None)
        resultados = {(r.criterio_id, r.pagina_id): r for r in auditoria.resultados.select_related("nao_conformidade")}
        grupos: OrderedDict[str, list] = OrderedDict()
        rotulos = dict(CriterioNormativo.PRINCIPIOS)
        for criterio in auditoria.base.criterios.all().order_by("principio", "codigo"):
            criterio.resultado = resultados.get((criterio.pk, pagina.pk)) if pagina else None
            grupos.setdefault(rotulos.get(criterio.principio, criterio.principio), []).append(criterio)
        return render(
            request,
            self.template_name,
            {
                "auditoria": auditoria,
                "paginas": paginas,
                "pagina": pagina,
                "grupos": grupos,
                "feitos": len(resultados),
                "esperado": auditoria.total_esperado(),
                "pode_editar": auditoria.auditor_id == request.user.pk and not auditoria.concluida,
            },
        )


class AvaliarView(PermissaoMixin, View):
    """Registro do resultado e, se Não Conforme, da não conformidade (UC-02 passo 5 / UC-03)."""

    acao_requerida = "auditoria.executar"
    template_name = "auditorias/avaliar.html"

    def _contexto(self, request, pk, criterio_id, pagina_id):
        auditoria = _auditoria_executavel(request, pk)
        criterio = get_object_or_404(auditoria.base.criterios, pk=criterio_id)
        pagina = get_object_or_404(auditoria.paginas, pk=pagina_id)
        resultado = (
            ResultadoChecklist.objects.filter(auditoria=auditoria, criterio=criterio, pagina=pagina)
            .select_related("nao_conformidade")
            .first()
        )
        nc = getattr(resultado, "nao_conformidade", None) if resultado else None
        return auditoria, criterio, pagina, resultado, nc

    def get(self, request, pk, criterio_id, pagina_id):
        auditoria, criterio, pagina, resultado, nc = self._contexto(request, pk, criterio_id, pagina_id)
        inicial = {}
        if resultado:
            inicial = {"status": resultado.status, "justificativa": resultado.justificativa}
        if nc:
            inicial.update(descricao=nc.descricao_falha, impacto=nc.impacto_usuario, alcance=nc.alcance_barreira)
        form = AvaliacaoForm(initial=inicial, evidencias_existentes=nc.evidencias.count() if nc else 0)
        return self._render(request, auditoria, criterio, pagina, nc, form)

    def post(self, request, pk, criterio_id, pagina_id):
        auditoria, criterio, pagina, resultado, nc = self._contexto(request, pk, criterio_id, pagina_id)
        if auditoria.concluida:
            messages.error(request, "A auditoria já foi concluída e não pode ser alterada.")
            return redirect("auditorias:checklist", pk=auditoria.pk)
        form = AvaliacaoForm(request.POST, request.FILES, evidencias_existentes=nc.evidencias.count() if nc else 0)
        if form.is_valid():
            try:
                resultado = registrar_avaliacao(auditoria, criterio, pagina, request.user, form.para_dados())
            except ValidationError as erro:
                form.add_error(None, erro)
            else:
                texto = f"{criterio.codigo}: {resultado.get_status_display()} registrado."
                nc = getattr(resultado, "nao_conformidade", None)
                if resultado.status == ResultadoChecklist.NAO_CONFORME and nc:
                    texto += f" Severidade calculada: {nc.get_nivel_severidade_display()} (pontuação {nc.pontuacao_severidade})."
                messages.success(request, texto)
                url = reverse("auditorias:checklist", kwargs={"pk": auditoria.pk})
                return redirect(f"{url}?pagina={pagina.pk}#criterio-{criterio.pk}")
        return self._render(request, auditoria, criterio, pagina, nc, form, status=400)

    def _render(self, request, auditoria, criterio, pagina, nc, form, status=200):
        return render(
            request,
            self.template_name,
            {
                "auditoria": auditoria,
                "criterio": criterio,
                "pagina": pagina,
                "nc": nc,
                "form": form,
            },
            status=status,
        )


class ConcluirView(PermissaoMixin, View):
    acao_requerida = "auditoria.executar"

    def post(self, request, pk):
        auditoria = _auditoria_executavel(request, pk)
        pendencias = concluir_auditoria(auditoria)
        if pendencias:
            return render(request, "auditorias/pendencias.html", {"auditoria": auditoria, "pendencias": pendencias}, status=409)
        messages.success(request, "Auditoria concluída. O relatório já pode ser exportado.")
        return redirect("relatorios:consulta", pk=auditoria.pk)


class SeveridadePreviaView(PermissaoMixin, View):
    """Prévia da severidade enquanto o auditor escolhe impacto e alcance (UC-03 passo 7)."""

    acao_requerida = "auditoria.executar"

    def get(self, request):
        try:
            s = calcular_severidade(request.GET.get("impacto", ""), request.GET.get("alcance", ""))
        except ValueError:
            return JsonResponse({"erro": "Informe impacto e alcance."}, status=400)
        return JsonResponse({"pontuacao": s.pontuacao, "nivel": s.nivel, "rotulo": ROTULO_NIVEL[s.nivel]})
