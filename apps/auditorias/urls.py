from django.urls import path

from . import views

app_name = "auditorias"
urlpatterns = [
    path("nova/", views.NovaAuditoriaView.as_view(), name="nova"),
    path("severidade/", views.SeveridadePreviaView.as_view(), name="severidade"),
    path("<int:pk>/", views.ChecklistView.as_view(), name="checklist"),
    path("<int:pk>/avaliar/<int:criterio_id>/<int:pagina_id>/", views.AvaliarView.as_view(), name="avaliar"),
    path("<int:pk>/concluir/", views.ConcluirView.as_view(), name="concluir"),
]
