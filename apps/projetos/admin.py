from django.contrib import admin

from .models import Pagina, Projeto


class PaginaInline(admin.TabularInline):
    model = Pagina
    extra = 0


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "esfera_orgao", "url_base", "data_criacao")
    inlines = [PaginaInline]
