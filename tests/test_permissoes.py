"""RF006 / RN05 — um teste por célula da matriz de permissões e autenticação."""

import pytest
from django.urls import reverse

from apps.auditorias.servicos import concluir_auditoria
from apps.relatorios.models import Relatorio
from tests.conftest import SENHA

PERMITIDO, NEGADO, LOGIN = "permitido", "negado", "login"


def _status_esperado(resposta, esperado):
    if esperado == PERMITIDO:
        # 409 = ação permitida, mas recusada pela regra de negócio (pendências)
        return resposta.status_code in (200, 302, 409) and "/contas/entrar/" not in resposta.get("Location", "")
    if esperado == NEGADO:
        return resposta.status_code == 403
    return resposta.status_code == 302 and "/contas/entrar/" in resposta["Location"]


def _concluida(auditoria, auditor):
    from apps.auditorias.servicos import DadosAvaliacao, registrar_avaliacao

    for p in auditoria.paginas.all():
        for c in auditoria.base.criterios.all():
            registrar_avaliacao(auditoria, c, p, auditor, DadosAvaliacao(status="CONFORME"))
    concluir_auditoria(auditoria)
    return auditoria


# (descrição, método, construtor de URL, auditor, gestor, anônimo)
CASOS = [
    ("UC-01 ver projetos", "get", lambda a: reverse("projetos:lista"), PERMITIDO, PERMITIDO, LOGIN),
    ("UC-01 cadastrar projeto", "get", lambda a: reverse("projetos:novo"), PERMITIDO, NEGADO, LOGIN),
    ("UC-01 adicionar página", "post", lambda a: reverse("projetos:detalhe", args=[a.projeto.pk]), PERMITIDO, NEGADO, LOGIN),
    ("UC-02 nova auditoria", "get", lambda a: reverse("auditorias:nova"), PERMITIDO, NEGADO, LOGIN),
    (
        "UC-02/03 avaliar critério",
        "get",
        lambda a: reverse("auditorias:avaliar", args=[a.pk, a.base.criterios.first().pk, a.paginas.first().pk]),
        PERMITIDO,
        NEGADO,
        LOGIN,
    ),
    ("UC-02 concluir", "post", lambda a: reverse("auditorias:concluir", args=[a.pk]), PERMITIDO, NEGADO, LOGIN),
    ("UC-04 consultar NCs", "get", lambda a: reverse("relatorios:consulta", args=[a.pk]), PERMITIDO, PERMITIDO, LOGIN),
]


@pytest.mark.parametrize(("descricao", "metodo", "url", "esp_auditor", "esp_gestor", "esp_anonimo"), CASOS, ids=[c[0] for c in CASOS])
def test_matriz_de_permissoes(client, auditor, gestor, auditoria, descricao, metodo, url, esp_auditor, esp_gestor, esp_anonimo):
    destino = url(auditoria)
    dados = {"nome_rota": "Nova", "url": "https://exemplo.gov.br/nova"} if "página" in descricao else {}
    for usuario, esperado in [(None, esp_anonimo), (gestor, esp_gestor), (auditor, esp_auditor)]:
        client.logout()
        if usuario:
            client.force_login(usuario)
        resposta = getattr(client, metodo)(destino, dados)
        assert _status_esperado(resposta, esperado), f"{descricao}: {usuario} esperava {esperado}, obteve {resposta.status_code}"


def test_exportar_permitido_para_auditor_dono_e_gestor(client, auditor, gestor, auditoria):
    _concluida(auditoria, auditor)
    url = reverse("relatorios:exportar", args=[auditoria.pk, "html"])
    for usuario in (auditor, gestor):
        client.force_login(usuario)
        assert client.post(url).status_code == 200
    client.logout()
    assert _status_esperado(client.post(url), LOGIN)


def test_auditor_nao_ve_auditoria_de_outro(client, outro_auditor, auditoria):
    client.force_login(outro_auditor)
    assert client.get(reverse("auditorias:checklist", args=[auditoria.pk])).status_code == 403
    assert client.get(reverse("relatorios:consulta", args=[auditoria.pk])).status_code == 403


@pytest.mark.parametrize("perfil", ["outro_auditor", "gestor"])
def test_registrar_nc_exige_auditor_responsavel(client, auditoria, perfil, request):
    client.force_login(request.getfixturevalue(perfil))
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = client.post(
        reverse("auditorias:avaliar", args=[auditoria.pk, c.pk, p.pk]),
        {"status": "NAO_CONFORME", "descricao": "Falha", "impacto": "MEDIO", "alcance": "GLOBAL", "observacao": "Evidência"},
    )
    assert r.status_code == 403
    assert not auditoria.resultados.exists()


def test_auditor_nao_exporta_auditoria_concluida_de_outro(client, outro_auditor, auditoria, auditor):
    _concluida(auditoria, auditor)
    client.force_login(outro_auditor)
    r = client.post(reverse("relatorios:exportar", args=[auditoria.pk, "html"]))
    assert r.status_code == 403
    assert not Relatorio.objects.exists()


def test_usuario_sem_perfil_e_negado(client, sem_perfil, auditoria):
    client.force_login(sem_perfil)
    assert client.get(reverse("projetos:lista")).status_code == 403


def test_login_e_logout(client, auditor):
    r = client.post(reverse("contas:entrar"), {"username": auditor.username, "password": SENHA})
    assert r.status_code == 302
    assert client.get(reverse("painel")).status_code == 200
    client.post(reverse("contas:sair"))
    assert client.get(reverse("painel")).status_code == 302


def test_mensagem_generica_em_credencial_invalida(client, auditor):
    r = client.post(reverse("contas:entrar"), {"username": "naoexiste@exemplo.org", "password": "x"})
    assert "E-mail ou senha inválidos" in r.content.decode()


def test_bloqueio_apos_cinco_tentativas(client, auditor):
    for _ in range(5):
        client.post(reverse("contas:entrar"), {"username": auditor.username, "password": "errada"})
    r = client.post(reverse("contas:entrar"), {"username": auditor.username, "password": SENHA})
    assert r.status_code == 200 and "bloqueado" in r.content.decode()


def test_health_check(client, db):
    assert client.get(reverse("saude")).json()["banco"] == "ok"
