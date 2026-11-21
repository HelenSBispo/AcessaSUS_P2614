from django.db import models


class CriterioNormativo(models.Model):
    """Pergunta de verificação redigida pela equipe e fundamentada em normas (RN01)."""

    PRINCIPIOS = [
        ("PERCEPTIVEL", "Perceptível"),
        ("OPERAVEL", "Operável"),
        ("COMPREENSIVEL", "Compreensível"),
        ("ROBUSTO", "Robusto"),
    ]

    codigo = models.CharField(max_length=10, unique=True)
    titulo = models.CharField(max_length=200)
    orientacao_verificacao = models.TextField("orientação de verificação")
    principio = models.CharField(max_length=20, choices=PRINCIPIOS)
    referencias_normativas = models.CharField("referências normativas", max_length=200)
    nivel_exigido = models.CharField("nível WCAG", max_length=3)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "critério normativo"
        verbose_name_plural = "critérios normativos"

    def __str__(self) -> str:
        return f"{self.codigo} — {self.titulo}"

    def obter_detalhes_diretriz(self) -> str:
        return f"{self.referencias_normativas} (nível {self.nivel_exigido})"


class BaseNormativa(models.Model):
    """Versão do checklist aplicada em uma auditoria (DM-03)."""

    nome = models.CharField(max_length=150)
    versao = models.CharField(max_length=20)
    data_publicacao = models.DateField()
    vigente = models.BooleanField(default=False)
    criterios = models.ManyToManyField(CriterioNormativo, related_name="bases")

    class Meta:
        ordering = ["-vigente", "-data_publicacao"]
        verbose_name = "base normativa (versão do checklist)"
        verbose_name_plural = "bases normativas (versões do checklist)"

    def __str__(self) -> str:
        return f"{self.nome} v{self.versao}"

    def listar_criterios(self):
        return self.criterios.all()
