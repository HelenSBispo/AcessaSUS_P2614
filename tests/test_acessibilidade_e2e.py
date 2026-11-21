"""RNF002 — verificação automática com axe-core nas telas do MVP (etapa 2 do procedimento do P1 §9.2).

Executar: pytest -m e2e  (requer Chromium do Playwright: `playwright install chromium`).
Regras: WCAG 2.0/2.1/2.2 níveis A e AA. Critério: 0 violações.
"""

import importlib
import os

import pytest
from django.core.management import call_command
from django.urls import reverse

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
SENHA = "Demo@AcessaSUS2026"


@pytest.fixture
def dados_demo(transactional_db):
    # Testes transacionais esvaziam o banco ao final; recarrega os dados das migrações de dados.
    from django.apps import apps as registro

    for modulo in ("apps.contas.migrations.0001_grupos_perfis", "apps.normas.migrations.0002_checklist_v1"):
        migracao = importlib.import_module(modulo)
        (getattr(migracao, "criar_grupos", None) or migracao.carregar)(registro, None)
    call_command("seed_demo", senha=SENHA, verbosity=0)


def _verificar(page, rotulo):
    from axe_playwright_python.sync_playwright import Axe

    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": TAGS}})
    violacoes = resultado.response["violations"]
    detalhes = "\n".join(f"- {v['id']} ({v['impact']}): {v['help']} — {len(v['nodes'])} elemento(s)" for v in violacoes)
    assert not violacoes, f"Violações de acessibilidade em {rotulo}:\n{detalhes}"


def _entrar(page, base, email):
    page.goto(base + reverse("contas:entrar"))
    page.get_by_label("E-mail").fill(email)
    page.get_by_label("Senha").fill(SENHA)
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_url(base + "/")


def test_telas_do_auditor(page, live_server, dados_demo):
    from apps.auditorias.models import Auditoria
    from apps.projetos.models import Projeto

    base = live_server.url
    page.goto(base + reverse("contas:entrar"))
    _verificar(page, "login")
    _entrar(page, base, "auditora@exemplo.org")
    andamento = Auditoria.objects.filter(status="EM_ANDAMENTO").first()
    projeto = Projeto.objects.first()
    criterio, pagina = andamento.base.criterios.first(), andamento.paginas.first()
    telas = {
        "painel": reverse("painel"),
        "projetos": reverse("projetos:lista"),
        "novo projeto": reverse("projetos:novo"),
        "detalhe do projeto": reverse("projetos:detalhe", args=[projeto.pk]),
        "nova auditoria": reverse("auditorias:nova") + f"?projeto={projeto.pk}",
        "checklist": reverse("auditorias:checklist", args=[andamento.pk]),
        "avaliar critério": reverse("auditorias:avaliar", args=[andamento.pk, criterio.pk, pagina.pk]),
    }
    for rotulo, caminho in telas.items():
        page.goto(base + caminho)
        _verificar(page, rotulo)


def test_telas_do_gestor(page, live_server, dados_demo):
    from apps.auditorias.models import Auditoria

    base = live_server.url
    _entrar(page, base, "gestor@exemplo.org")
    concluida = Auditoria.objects.filter(status="CONCLUIDA").first()
    page.goto(base + reverse("relatorios:consulta", args=[concluida.pk]))
    _verificar(page, "não conformidades por severidade")
