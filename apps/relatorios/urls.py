from django.urls import path

from . import views

app_name = "relatorios"
urlpatterns = [
    path("<int:pk>/", views.ConsultaView.as_view(), name="consulta"),
    path("<int:pk>/exportar/<str:formato>/", views.ExportarView.as_view(), name="exportar"),
]
