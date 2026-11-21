import logging

from django.contrib.auth.views import LoginView, LogoutView
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from .forms import EntrarForm

logger = logging.getLogger("acessasus.acesso")


class EntrarView(LoginView):
    template_name = "contas/entrar.html"
    authentication_form = EntrarForm
    redirect_authenticated_user = True


class SairView(LogoutView):
    pass


def acesso_negado(request, exception=None):
    return render(request, "403.html", status=403)


def saude(request):
    """Health check simples para a demonstração/implantação."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        banco = "ok"
    except Exception:  # pragma: no cover - depende do ambiente
        logger.exception("falha no health check do banco")
        banco = "erro"
    status = 200 if banco == "ok" else 503
    return JsonResponse({"status": "ok" if status == 200 else "erro", "banco": banco}, status=status)
