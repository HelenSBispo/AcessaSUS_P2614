from django.urls import path

from . import views

app_name = "projetos"
urlpatterns = [
    path("", views.ProjetoListaView.as_view(), name="lista"),
    path("novo/", views.ProjetoCriarView.as_view(), name="novo"),
    path("<int:pk>/", views.ProjetoDetalheView.as_view(), name="detalhe"),
]
