from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView

from apps.contas.perfis import PermissaoMixin, negar, possui_permissao

from .forms import PaginaForm, ProjetoForm
from .models import Projeto


class ProjetoListaView(PermissaoMixin, ListView):
    acao_requerida = "projeto.ver"
    model = Projeto
    template_name = "projetos/lista.html"
    context_object_name = "projetos"

    def get_queryset(self):
        return Projeto.objects.prefetch_related("paginas")


class ProjetoCriarView(PermissaoMixin, CreateView):
    acao_requerida = "projeto.editar"
    model = Projeto
    form_class = ProjetoForm
    template_name = "projetos/form.html"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        resposta = super().form_valid(form)
        messages.success(self.request, "Projeto cadastrado. Agora adicione as páginas a auditar.")
        return resposta

    def get_success_url(self):
        return reverse("projetos:detalhe", kwargs={"pk": self.object.pk})


class ProjetoDetalheView(PermissaoMixin, View):
    """Detalhe do projeto e inclusão de páginas (UC-01)."""

    acao_requerida = "projeto.ver"
    template_name = "projetos/detalhe.html"

    def get(self, request, pk):
        projeto = get_object_or_404(Projeto, pk=pk)
        return render(request, self.template_name, {"projeto": projeto, "form": PaginaForm()})

    def post(self, request, pk):
        if not possui_permissao(request.user, "projeto.editar"):
            negar(request.user, "projeto.editar")
        projeto = get_object_or_404(Projeto, pk=pk)
        form = PaginaForm(request.POST)
        if form.is_valid():
            try:
                projeto.adicionar_pagina(form.cleaned_data["nome_rota"], form.cleaned_data["url"])
            except ValidationError as erro:
                form.add_error("url", erro)
            else:
                messages.success(request, "Página adicionada.")
                return redirect("projetos:detalhe", pk=projeto.pk)
        return render(request, self.template_name, {"projeto": projeto, "form": form}, status=400)
