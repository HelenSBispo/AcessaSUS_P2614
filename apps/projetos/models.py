from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .validacao import validar_url_sem_dado_pessoal


class Projeto(models.Model):
    nome = models.CharField("nome do projeto", max_length=150)
    esfera_orgao = models.CharField("órgão/esfera responsável", max_length=150)
    url_base = models.URLField("URL base", validators=[validar_url_sem_dado_pessoal])
    descricao = models.TextField("descrição", blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="projetos")
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    def adicionar_pagina(self, nome_rota: str, url: str) -> "Pagina":
        """Cria a página após validar URL e duplicidade (MOD-01, SD-01)."""
        validar_url_sem_dado_pessoal(url)
        if self.paginas.filter(url=url).exists():
            raise ValidationError("Esta URL já está cadastrada neste projeto.", code="duplicada")
        return self.paginas.create(nome_rota=nome_rota, url=url)

    def listar_paginas_mapeadas(self):
        return self.paginas.all()


class Pagina(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="paginas")
    nome_rota = models.CharField("nome da rota", max_length=120)
    url = models.URLField("URL", validators=[validar_url_sem_dado_pessoal])

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["projeto", "url"], name="pagina_url_unica_por_projeto")]

    def __str__(self) -> str:
        return f"{self.nome_rota} — {self.url}"
