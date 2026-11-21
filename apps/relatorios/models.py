from django.conf import settings
from django.db import models

from apps.auditorias.models import Auditoria


class Relatorio(models.Model):
    """Registro de emissão de relatório (DM-08). Só é criado após geração bem-sucedida."""

    PDF, HTML = "PDF", "HTML"
    FORMATOS = [(PDF, "PDF"), (HTML, "HTML")]

    auditoria = models.ForeignKey(Auditoria, on_delete=models.CASCADE, related_name="relatorios")
    formato = models.CharField(max_length=4, choices=FORMATOS)
    gerado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data_geracao = models.DateTimeField(auto_now_add=True)
    duracao_ms = models.PositiveIntegerField(default=0, help_text="Tempo de geração (medição do RNF003).")

    class Meta:
        ordering = ["-data_geracao"]

    def __str__(self) -> str:
        return f"Relatório {self.formato} da auditoria #{self.auditoria_id} em {self.data_geracao:%d/%m/%Y %H:%M}"
