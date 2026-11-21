from django.contrib import admin

from .models import BaseNormativa, CriterioNormativo


@admin.register(CriterioNormativo)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "titulo", "principio", "referencias_normativas", "nivel_exigido")


@admin.register(BaseNormativa)
class BaseAdmin(admin.ModelAdmin):
    list_display = ("nome", "versao", "vigente", "data_publicacao")
    filter_horizontal = ("criterios",)
