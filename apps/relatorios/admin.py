from django.contrib import admin

from .models import Relatorio


@admin.register(Relatorio)
class RelatorioAdmin(admin.ModelAdmin):
    list_display = ("auditoria", "formato", "gerado_por", "data_geracao", "duracao_ms")
