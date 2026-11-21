"""RF002, RF003, RN01, RN02 — checklist, não conformidade e conclusão."""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.auditorias.models import Evidencia, NaoConformidade, ResultadoChecklist
from apps.auditorias.servicos import DadosAvaliacao, concluir_auditoria, registrar_avaliacao

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _url_avaliar(aud, criterio, pagina):
    return reverse("auditorias:avaliar", args=[aud.pk, criterio.pk, pagina.pk])


def test_iniciar_auditoria_pela_tela(cliente_auditor, projeto, base):
    r = cliente_auditor.post(
        reverse("auditorias:nova"), {"projeto": projeto.pk, "paginas": [p.pk for p in projeto.paginas.all()], "base": base.pk}
    )
    assert r.status_code == 302
    aud = projeto.auditorias.get()
    assert aud.status == "EM_ANDAMENTO" and aud.base == base and aud.paginas.count() == 2


def test_nao_aplicavel_exige_justificativa(cliente_auditor, auditoria):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(_url_avaliar(auditoria, c, p), {"status": "NAO_APLICAVEL", "justificativa": ""})
    assert r.status_code == 400
    assert not ResultadoChecklist.objects.exists()


def test_nc_apenas_com_observacao_textual_e_aceita(cliente_auditor, auditoria):
    """RN02 (v1.1): a observação textual sozinha é evidência válida."""
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p),
        {
            "status": "NAO_CONFORME",
            "descricao": "Botão sem nome acessível.",
            "impacto": "CRITICO",
            "alcance": "PONTUAL",
            "observacao": "Verificado com NVDA.",
        },
    )
    assert r.status_code == 302
    nc = NaoConformidade.objects.get()
    assert nc.nivel_severidade == "ALTA" and nc.pontuacao_severidade == 4
    assert nc.evidencias.get().tipo == Evidencia.OBSERVACAO
    assert nc.verificar_completude()


def test_nc_sem_evidencia_e_bloqueada(cliente_auditor, auditoria):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p), {"status": "NAO_CONFORME", "descricao": "Falha", "impacto": "BAIXO", "alcance": "PONTUAL"}
    )
    assert r.status_code == 400
    assert "RN02" in r.content.decode()
    assert not ResultadoChecklist.objects.exists() and not NaoConformidade.objects.exists()


def test_nc_sem_parametros_nao_exibe_severidade(cliente_auditor, auditoria):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(_url_avaliar(auditoria, c, p), {"status": "NAO_CONFORME", "descricao": "Falha", "observacao": "obs"})
    assert r.status_code == 400
    assert not NaoConformidade.objects.exists()


def test_servico_e_transacional_quando_rn02_falha(auditoria, auditor):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    with pytest.raises(ValidationError):
        registrar_avaliacao(
            auditoria, c, p, auditor, DadosAvaliacao(status="NAO_CONFORME", descricao="x", impacto="BAIXO", alcance="PONTUAL")
        )
    assert not ResultadoChecklist.objects.exists()


def test_captura_valida_e_anexada(cliente_auditor, auditoria):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    arquivo = SimpleUploadedFile("tela.png", PNG, content_type="image/png")
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p),
        {
            "status": "NAO_CONFORME",
            "descricao": "Falha",
            "impacto": "MEDIO",
            "alcance": "GLOBAL",
            "captura": arquivo,
        },
    )
    assert r.status_code == 302
    ev = Evidencia.objects.get()
    assert ev.tipo == Evidencia.CAPTURA and ev.arquivo.name.endswith(".png")


@pytest.mark.parametrize(
    ("nome", "conteudo"),
    [("tela.gif", b"GIF89a"), ("falsa.png", b"nao-e-png"), ("grande.png", b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 1))],
)
def test_captura_invalida_e_rejeitada(cliente_auditor, auditoria, nome, conteudo):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    arquivo = SimpleUploadedFile(nome, conteudo)
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p),
        {
            "status": "NAO_CONFORME",
            "descricao": "Falha",
            "impacto": "MEDIO",
            "alcance": "GLOBAL",
            "captura": arquivo,
        },
    )
    assert r.status_code == 400
    assert not Evidencia.objects.exists()


def test_trocar_para_conforme_descarta_nc_e_arquivos(auditoria, auditor):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    arquivo = SimpleUploadedFile("tela.png", PNG)
    registrar_avaliacao(
        auditoria,
        c,
        p,
        auditor,
        DadosAvaliacao(
            status="NAO_CONFORME", descricao="x", impacto="BAIXO", alcance="PONTUAL", evidencias=[(Evidencia.CAPTURA, "", arquivo)]
        ),
    )
    caminho = Evidencia.objects.get().arquivo.path
    registrar_avaliacao(auditoria, c, p, auditor, DadosAvaliacao(status="CONFORME"))
    assert not NaoConformidade.objects.exists()
    assert io.open is not None and not __import__("os").path.exists(caminho)


def _preencher(auditoria, auditor, exceto=0):
    combos = [(c, p) for p in auditoria.paginas.all() for c in auditoria.base.criterios.all()]
    for c, p in combos[: len(combos) - exceto]:
        registrar_avaliacao(auditoria, c, p, auditor, DadosAvaliacao(status="CONFORME"))


def test_conclusao_com_pendencias_e_bloqueada(cliente_auditor, auditoria, auditor):
    _preencher(auditoria, auditor, exceto=1)
    r = cliente_auditor.post(reverse("auditorias:concluir", args=[auditoria.pk]))
    assert r.status_code == 409
    auditoria.refresh_from_db()
    assert auditoria.status == "EM_ANDAMENTO"


def test_conclusao_sem_pendencias(cliente_auditor, auditoria, auditor):
    _preencher(auditoria, auditor)
    r = cliente_auditor.post(reverse("auditorias:concluir", args=[auditoria.pk]))
    assert r.status_code == 302
    auditoria.refresh_from_db()
    assert auditoria.status == "CONCLUIDA" and auditoria.data_conclusao


def test_auditoria_concluida_nao_aceita_alteracao(auditoria, auditor):
    _preencher(auditoria, auditor)
    assert concluir_auditoria(auditoria) == []
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    with pytest.raises(ValidationError):
        registrar_avaliacao(auditoria, c, p, auditor, DadosAvaliacao(status="CONFORME"))


def test_previa_de_severidade(cliente_auditor):
    r = cliente_auditor.get(reverse("auditorias:severidade"), {"impacto": "ALTO", "alcance": "PONTUAL"})
    assert r.json() == {"pontuacao": 3, "nivel": "MEDIA", "rotulo": "Média"}


def test_telas_principais_renderizam(cliente_auditor, auditoria):
    for url in [
        reverse("painel"),
        reverse("projetos:lista"),
        reverse("auditorias:nova"),
        reverse("auditorias:checklist", args=[auditoria.pk]),
    ]:
        assert cliente_auditor.get(url).status_code == 200
