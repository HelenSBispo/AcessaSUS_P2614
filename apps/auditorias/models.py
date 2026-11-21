from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from apps.normas.models import BaseNormativa, CriterioNormativo
from apps.projetos.models import Pagina, Projeto
from apps.severidade.regra import ORDEM_NIVEL, calcular_severidade


class Auditoria(models.Model):
    EM_ANDAMENTO, CONCLUIDA = "EM_ANDAMENTO", "CONCLUIDA"
    STATUS = [(EM_ANDAMENTO, "Em andamento"), (CONCLUIDA, "Concluída")]

    projeto = models.ForeignKey(Projeto, on_delete=models.PROTECT, related_name="auditorias")
    auditor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="auditorias")
    base = models.ForeignKey(BaseNormativa, on_delete=models.PROTECT, related_name="auditorias", verbose_name="base normativa")
    paginas = models.ManyToManyField(Pagina, related_name="auditorias", verbose_name="páginas abrangidas")
    status = models.CharField(max_length=20, choices=STATUS, default=EM_ANDAMENTO)
    data_inicio = models.DateTimeField(default=timezone.now)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-data_inicio"]

    def __str__(self) -> str:
        return f"Auditoria #{self.pk} — {self.projeto}"

    @property
    def concluida(self) -> bool:
        return self.status == self.CONCLUIDA

    def obter_status(self) -> str:
        return self.status

    def obter_resultados(self):
        return self.resultados.select_related("criterio", "pagina")

    def total_esperado(self) -> int:
        return self.base.criterios.count() * self.paginas.count()

    def verificar_pendencias(self) -> list[str]:
        """Combinações critério × página ainda sem resultado (SD-02)."""
        feitos = set(self.resultados.values_list("criterio_id", "pagina_id"))
        pendencias = []
        for pagina in self.paginas.all():
            for criterio in self.base.criterios.all():
                if (criterio.pk, pagina.pk) not in feitos:
                    pendencias.append(f"{criterio.codigo} em {pagina.nome_rota}")
        return pendencias

    def concluir(self) -> None:
        pendencias = self.verificar_pendencias()
        if pendencias:
            raise ValidationError("Há avaliações pendentes.", code="pendencias", params={"pendencias": pendencias})
        self.status = self.CONCLUIDA
        self.data_conclusao = timezone.now()
        self.save(update_fields=["status", "data_conclusao"])

    def listar_apontamentos_por_severidade(self, filtros: dict | None = None):
        """Resultados Não Conformes ordenados Alta → Baixa, empate pela pontuação (RF004)."""
        filtros = filtros or {}
        qs = (
            self.resultados.filter(status=ResultadoChecklist.NAO_CONFORME, nao_conformidade__isnull=False)
            .select_related("criterio", "pagina", "nao_conformidade")
            .prefetch_related("nao_conformidade__evidencias")
        )
        if filtros.get("severidade"):
            qs = qs.filter(nao_conformidade__nivel_severidade=filtros["severidade"])
        if filtros.get("pagina"):
            qs = qs.filter(pagina_id=filtros["pagina"])
        if filtros.get("principio"):
            qs = qs.filter(criterio__principio=filtros["principio"])
        rank = Case(
            *[When(nao_conformidade__nivel_severidade=n, then=Value(o)) for n, o in ORDEM_NIVEL.items()],
            default=Value(0),
            output_field=IntegerField(),
        )
        return qs.annotate(rank_severidade=rank).order_by(
            "-rank_severidade", "-nao_conformidade__pontuacao_severidade", "criterio__codigo", "pagina_id"
        )


class ResultadoChecklist(models.Model):
    """Avaliação de um critério em uma página (Avaliação de Critério no domínio)."""

    CONFORME, NAO_CONFORME, NAO_APLICAVEL = "CONFORME", "NAO_CONFORME", "NAO_APLICAVEL"
    STATUS = [(CONFORME, "Conforme"), (NAO_CONFORME, "Não Conforme"), (NAO_APLICAVEL, "Não Aplicável")]

    auditoria = models.ForeignKey(Auditoria, on_delete=models.CASCADE, related_name="resultados")
    criterio = models.ForeignKey(CriterioNormativo, on_delete=models.PROTECT)
    pagina = models.ForeignKey(Pagina, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS)
    justificativa = models.TextField(blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["auditoria", "criterio", "pagina"], name="resultado_unico_por_combinacao")]

    def __str__(self) -> str:
        return f"{self.criterio.codigo} / {self.pagina.nome_rota}: {self.get_status_display()}"

    def registrar_avaliacao(self, status: str, justificativa: str = "") -> None:
        if status not in dict(self.STATUS):
            raise ValidationError("Resultado inválido.")
        if status == self.NAO_APLICAVEL and not justificativa.strip():
            raise ValidationError("O resultado Não Aplicável exige justificativa.", code="justificativa")
        self.status = status
        self.justificativa = justificativa.strip() if status == self.NAO_APLICAVEL else ""

    def obter_detalhes(self) -> dict:
        detalhes = {"criterio": str(self.criterio), "referencia": self.criterio.obter_detalhes_diretriz(), "pagina": self.pagina.url}
        nc = getattr(self, "nao_conformidade", None)
        if nc:
            detalhes.update(nc.obter_detalhes())
        return detalhes


class NaoConformidade(models.Model):
    IMPACTOS = [
        ("BAIXO", "Baixo — incomoda, mas não impede"),
        ("MEDIO", "Médio — dificulta, há contorno"),
        ("ALTO", "Alto — exige ajuda de terceiros ou grande esforço"),
        ("CRITICO", "Crítico — impede a tarefa principal"),
    ]
    ALCANCES = [
        ("PONTUAL", "Pontual — um elemento ou página"),
        ("PARCIAL", "Parcial — várias páginas ou uma jornada"),
        ("GLOBAL", "Global — todas as páginas"),
    ]
    NIVEIS = [("BAIXA", "Baixa"), ("MEDIA", "Média"), ("ALTA", "Alta")]

    resultado = models.OneToOneField(ResultadoChecklist, on_delete=models.CASCADE, related_name="nao_conformidade")
    descricao_falha = models.TextField("descrição da falha")
    impacto_usuario = models.CharField("impacto no usuário", max_length=10, choices=IMPACTOS)
    alcance_barreira = models.CharField("alcance da barreira", max_length=10, choices=ALCANCES)
    pontuacao_severidade = models.PositiveSmallIntegerField(editable=False)
    nivel_severidade = models.CharField(max_length=5, choices=NIVEIS, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"NC {self.resultado} — {self.get_nivel_severidade_display()}"

    def save(self, *args, **kwargs):
        self.calcular_severidade()
        super().save(*args, **kwargs)

    @property
    def impacto_curto(self) -> str:
        return self.get_impacto_usuario_display().split(" — ")[0]

    @property
    def alcance_curto(self) -> str:
        return self.get_alcance_barreira_display().split(" — ")[0]

    def definir_descricao(self, descricao: str) -> None:
        self.descricao_falha = descricao.strip()

    def informar_parametros(self, impacto: str, alcance: str) -> str:
        self.impacto_usuario = impacto
        self.alcance_barreira = alcance
        self.calcular_severidade()
        return self.nivel_severidade

    def calcular_severidade(self) -> None:
        resultado = calcular_severidade(self.impacto_usuario, self.alcance_barreira)
        self.pontuacao_severidade = resultado.pontuacao
        self.nivel_severidade = resultado.nivel

    def verificar_completude(self) -> bool:
        """RN02: descrição, ≥ 1 evidência e severidade calculada."""
        return bool(self.descricao_falha and self.nivel_severidade and self.pk and self.evidencias.exists())

    def obter_detalhes(self) -> dict:
        return {
            "descricao": self.descricao_falha,
            "impacto": self.get_impacto_usuario_display(),
            "alcance": self.get_alcance_barreira_display(),
            "pontuacao": self.pontuacao_severidade,
            "severidade": self.get_nivel_severidade_display(),
            "evidencias": [str(e) for e in self.evidencias.all()],
        }


def caminho_evidencia(instancia, nome_arquivo: str) -> str:
    return timezone.now().strftime("evidencias/%Y/%m/") + nome_arquivo


class Evidencia(models.Model):
    CAPTURA, CODIGO, URL, OBSERVACAO = "CAPTURA_TELA", "TRECHO_CODIGO", "URL", "OBSERVACAO_TEXTUAL"
    TIPOS = [(CAPTURA, "Captura de tela"), (CODIGO, "Trecho de código"), (URL, "URL"), (OBSERVACAO, "Observação textual")]

    nao_conformidade = models.ForeignKey(NaoConformidade, on_delete=models.CASCADE, related_name="evidencias")
    tipo = models.CharField(max_length=20, choices=TIPOS)
    arquivo = models.FileField(upload_to=caminho_evidencia, blank=True)
    conteudo = models.TextField(blank=True, help_text="Texto da observação, trecho de código ou URL.")
    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        if self.tipo == self.CAPTURA:
            return f"Captura de tela: {self.arquivo.name.rsplit('/', 1)[-1]}"
        return f"{self.get_tipo_display()}: {self.conteudo[:80]}"

    def descartar(self) -> None:
        self.delete()
