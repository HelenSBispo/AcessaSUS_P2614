from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.auditorias.views import PainelView
from apps.contas.views import saude

urlpatterns = [
    path("", PainelView.as_view(), name="painel"),
    path("saude/", saude, name="saude"),
    path("contas/", include("apps.contas.urls")),
    path("projetos/", include("apps.projetos.urls")),
    path("auditorias/", include("apps.auditorias.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "apps.contas.views.acesso_negado"
