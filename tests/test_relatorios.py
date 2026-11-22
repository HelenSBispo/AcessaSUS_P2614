"""RF004 (ordenação), RF005, RN06 — consulta e exportação."""

import pytest
from django.urls import reverse

from apps.auditorias.models import Evidencia
from apps.auditorias.servicos import DadosAvaliacao, concluir_auditoria, registrar_avaliacao
from apps.relatorios.models import Relatorio

NCS = {0: ("BAIXO", "PARCIAL"), 1: ("CRITICO", "PONTUAL"), 2: ("MEDIO", "GLOBAL"), 3: ("CRITICO", "PARCIAL")}


@pytest.fixture
def auditoria_com_ncs(auditoria, auditor):
    pagina = auditoria.paginas.first()
    for i, c in enumerate(auditoria.base.criterios.all()):
        for p in auditoria.paginas.all():
            if p == pagina and i in NCS:
                imp, alc = NCS[i]
                dados = DadosAvaliacao(
                    status="NAO_CONFORME",
                    descricao=f"Falha {c.codigo}",
                    impacto=imp,
                    alcance=alc,
                    evidencias=[(Evidencia.OBSERVACAO, "obs", None)],
                )
            else:
                dados = DadosAvaliacao(status="CONFORME")
            registrar_avaliacao(auditoria, c, p, auditor, dados)
    return auditoria


def test_ordenacao_alta_media_baixa_com_desempate(auditoria_com_ncs):
    ordem = [
        (r.nao_conformidade.nivel_severidade, r.nao_conformidade.pontuacao_severidade)
        for r in auditoria_com_ncs.listar_apontamentos_por_severidade()
    ]
    assert ordem == [("ALTA", 8), ("ALTA", 4), ("MEDIA", 6), ("BAIXA", 2)]


def test_filtro_por_severidade(auditoria_com_ncs):
    assert {r.nao_conformidade.nivel_severidade for r in auditoria_com_ncs.listar_apontamentos_por_severidade({"severidade": "ALTA"})} == {
        "ALTA"
    }


def test_exportacao_bloqueada_em_andamento(cliente_gestor, auditoria_com_ncs):
    r = cliente_gestor.post(reverse("relatorios:exportar", args=[auditoria_com_ncs.pk, "pdf"]))
    assert r.status_code == 302
    assert not Relatorio.objects.exists()


def test_exportar_html_de_auditoria_concluida(cliente_gestor, auditoria_com_ncs):
    concluir_auditoria(auditoria_com_ncs)
    r = cliente_gestor.post(reverse("relatorios:exportar", args=[auditoria_com_ncs.pk, "html"]))
    assert r.status_code == 200 and r["Content-Type"].startswith("text/html")
    html = r.content.decode()
    assert html.index("Falha") < html.index("Resultados de todos")
    assert Relatorio.objects.get().formato == "HTML"


def test_exportar_pdf_de_auditoria_concluida(cliente_gestor, auditoria_com_ncs):
    concluir_auditoria(auditoria_com_ncs)
    r = cliente_gestor.post(reverse("relatorios:exportar", args=[auditoria_com_ncs.pk, "pdf"]))
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    rel = Relatorio.objects.get()
    assert rel.formato == "PDF"
    assert rel.duracao_ms < 3000  # RNF003 (indicativo, medição isolada)


def test_falha_na_geracao_nao_registra_emissao(cliente_gestor, auditoria_com_ncs, monkeypatch):
    concluir_auditoria(auditoria_com_ncs)

    def falhar(*a, **k):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("apps.relatorios.views.gerar_pdf", falhar)
    r = cliente_gestor.post(reverse("relatorios:exportar", args=[auditoria_com_ncs.pk, "pdf"]))
    assert r.status_code == 302
    assert not Relatorio.objects.exists()


def test_consulta_renderiza(cliente_gestor, auditoria_com_ncs):
    r = cliente_gestor.get(reverse("relatorios:consulta", args=[auditoria_com_ncs.pk]))
    assert r.status_code == 200 and "Alta" in r.content.decode()


def test_formato_invalido_nega_exportacao(cliente_gestor, auditoria):
    r = cliente_gestor.post(reverse("relatorios:exportar", args=[auditoria.pk, "csv"]))
    assert r.status_code == 403
    assert not Relatorio.objects.exists()
