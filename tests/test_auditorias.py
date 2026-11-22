"""RF002, RF003, RN01, RN02 — checklist, não conformidade e conclusão."""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.auditorias.models import Auditoria, Evidencia, NaoConformidade, ResultadoChecklist
from apps.auditorias.servicos import DadosAvaliacao, concluir_auditoria, iniciar_auditoria, registrar_avaliacao
from apps.normas.models import BaseNormativa
from apps.projetos.models import Projeto

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


def test_nao_inicia_auditoria_com_base_sem_criterios(cliente_auditor, projeto, base):
    vazia = BaseNormativa.objects.create(nome="Base de teste", versao="0.1", data_publicacao=base.data_publicacao)
    r = cliente_auditor.post(reverse("auditorias:nova"), {"projeto": projeto.pk, "paginas": [projeto.paginas.first().pk], "base": vazia.pk})
    assert r.status_code == 400
    assert "A base normativa selecionada não possui critérios." in r.context["form"].non_field_errors()
    assert not projeto.auditorias.exists()


@pytest.mark.parametrize(
    ("fora_do_projeto", "mensagem"),
    [(False, "Selecione ao menos uma página"), (True, "devem pertencer ao projeto selecionado")],
)
def test_servico_de_inicio_recusa_paginas_invalidas(projeto, base, auditor, fora_do_projeto, mensagem):
    paginas = []
    if fora_do_projeto:
        outro = Projeto.objects.create(
            nome="Outro portal", esfera_orgao="SMS fictícia", url_base="https://outro.exemplo.org", criado_por=auditor
        )
        paginas = [projeto.paginas.first(), outro.adicionar_pagina("Inicial", outro.url_base)]
    with pytest.raises(ValidationError, match=mensagem):
        iniciar_auditoria(projeto, paginas, base, auditor)
    assert not Auditoria.objects.exists()


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


def test_nc_sem_descricao_e_recusada(cliente_auditor, auditoria):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p),
        {"status": "NAO_CONFORME", "descricao": " ", "impacto": "BAIXO", "alcance": "PONTUAL", "observacao": "Evidência"},
    )
    assert r.status_code == 400
    assert "Descreva a falha encontrada." in r.context["form"].errors["descricao"]
    assert not auditoria.resultados.exists()


@pytest.mark.parametrize(
    ("dados", "mensagem"),
    [
        (DadosAvaliacao(status="INVALIDO"), "Resultado inválido"),
        (DadosAvaliacao(status="NAO_APLICAVEL"), "exige justificativa"),
        (DadosAvaliacao(status="NAO_CONFORME"), "Descreva a falha"),
        (DadosAvaliacao(status="NAO_CONFORME", descricao="Falha"), "Informe o impacto e o alcance"),
    ],
)
def test_servico_recusa_avaliacoes_incompletas(auditoria, auditor, dados, mensagem):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    with pytest.raises(ValidationError, match=mensagem):
        registrar_avaliacao(auditoria, c, p, auditor, dados)
    assert not auditoria.resultados.exists()
    assert not NaoConformidade.objects.exists()


def test_servico_recusa_resultado_para_pagina_fora_da_auditoria(auditoria, auditor):
    c = auditoria.base.criterios.first()
    p = auditoria.projeto.adicionar_pagina("Fora do escopo", "https://exemplo.gov.br/fora")
    with pytest.raises(ValidationError, match="A página não faz parte desta auditoria"):
        registrar_avaliacao(auditoria, c, p, auditor, DadosAvaliacao(status="CONFORME"))
    assert not auditoria.resultados.exists()


def test_servico_recusa_criterio_fora_da_base(auditoria, auditor):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    auditoria.base.criterios.remove(c)
    with pytest.raises(ValidationError, match="O critério não pertence à base normativa"):
        registrar_avaliacao(auditoria, c, p, auditor, DadosAvaliacao(status="CONFORME"))
    assert not auditoria.resultados.exists()


def test_falha_no_armazenamento_reverte_alteracao_da_nc(auditoria, auditor, monkeypatch):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    resultado = registrar_avaliacao(
        auditoria,
        c,
        p,
        auditor,
        DadosAvaliacao(
            status="NAO_CONFORME",
            descricao="Falha original",
            impacto="BAIXO",
            alcance="PONTUAL",
            evidencias=[(Evidencia.OBSERVACAO, "Evidência original", None)],
        ),
    )
    nc = resultado.nao_conformidade
    evidencia = nc.evidencias.get()

    def falhar(*args, **kwargs):
        raise OSError("armazenamento indisponível")

    monkeypatch.setattr(evidencia.arquivo.storage, "save", falhar)
    with pytest.raises(OSError, match="armazenamento indisponível"):
        registrar_avaliacao(
            auditoria,
            c,
            p,
            auditor,
            DadosAvaliacao(
                status="NAO_CONFORME",
                descricao="Falha atualizada",
                impacto="CRITICO",
                alcance="GLOBAL",
                evidencias=[
                    (Evidencia.OBSERVACAO, "Evidência nova", None),
                    (Evidencia.CAPTURA, "", SimpleUploadedFile("tela.png", PNG)),
                ],
            ),
        )
    nc.refresh_from_db()
    assert (nc.descricao_falha, nc.nivel_severidade) == ("Falha original", "BAIXA")
    assert nc.evidencias.get() == evidencia
    assert auditoria.resultados.get() == resultado


def test_servico_e_transacional_quando_rn02_falha(auditoria, auditor):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    with pytest.raises(ValidationError, match="RN02"):
        registrar_avaliacao(
            auditoria, c, p, auditor, DadosAvaliacao(status="NAO_CONFORME", descricao="x", impacto="BAIXO", alcance="PONTUAL")
        )
    assert not ResultadoChecklist.objects.exists()
    assert not NaoConformidade.objects.exists()
    assert not Evidencia.objects.exists()


@pytest.mark.parametrize(
    ("campo", "tipo", "conteudo"),
    [("trecho_codigo", Evidencia.CODIGO, "<button></button>"), ("url_evidencia", Evidencia.URL, "https://exemplo.gov.br/agendar")],
)
def test_evidencia_textual_e_vinculada_ao_resultado(cliente_auditor, auditoria, campo, tipo, conteudo):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p),
        {"status": "NAO_CONFORME", "descricao": "Falha", "impacto": "MEDIO", "alcance": "GLOBAL", campo: conteudo},
    )
    assert r.status_code == 302
    resultado = auditoria.resultados.get(criterio=c, pagina=p)
    assert resultado.status == ResultadoChecklist.NAO_CONFORME
    evidencia = resultado.nao_conformidade.evidencias.get()
    assert (evidencia.tipo, evidencia.conteudo) == (tipo, conteudo)


def test_url_de_evidencia_com_parametro_pessoal_e_recusada(cliente_auditor, auditoria):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(
        _url_avaliar(auditoria, c, p),
        {
            "status": "NAO_CONFORME",
            "descricao": "Falha",
            "impacto": "MEDIO",
            "alcance": "GLOBAL",
            "observacao": "Outra evidência válida.",
            "url_evidencia": "https://exemplo.gov.br/agendar?cns=0",
        },
    )
    assert r.status_code == 400
    assert "RN04" in r.context["form"].errors["url_evidencia"][0]
    assert not auditoria.resultados.exists()
    assert not NaoConformidade.objects.exists()
    assert not Evidencia.objects.exists()


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


def test_editar_nc_mantem_captura_e_recalcula_severidade(cliente_auditor, auditoria, auditor):
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    resultado = registrar_avaliacao(
        auditoria,
        c,
        p,
        auditor,
        DadosAvaliacao(
            status="NAO_CONFORME",
            descricao="Falha original",
            impacto="BAIXO",
            alcance="PONTUAL",
            evidencias=[(Evidencia.CAPTURA, "", SimpleUploadedFile("original.png", PNG))],
        ),
    )
    nc = resultado.nao_conformidade
    evidencia = nc.evidencias.get()
    url = _url_avaliar(auditoria, c, p)
    r = cliente_auditor.get(url)
    assert r.status_code == 200
    assert r.context["form"].initial["descricao"] == "Falha original"
    assert "Captura de tela:" in r.content.decode()
    r = cliente_auditor.post(url, {"status": "NAO_CONFORME", "descricao": "Falha revista", "impacto": "ALTO", "alcance": "PONTUAL"})
    assert r.status_code == 302
    assert auditoria.resultados.get() == resultado
    nc.refresh_from_db()
    assert (nc.descricao_falha, nc.nivel_severidade, nc.pontuacao_severidade) == ("Falha revista", "MEDIA", 3)
    assert nc.evidencias.get() == evidencia
    with evidencia.arquivo.open("rb") as arquivo:
        assert arquivo.read() == PNG


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


def test_post_nao_altera_avaliacao_de_auditoria_concluida(cliente_auditor, auditoria, auditor):
    _preencher(auditoria, auditor)
    assert concluir_auditoria(auditoria) == []
    c, p = auditoria.base.criterios.first(), auditoria.paginas.first()
    r = cliente_auditor.post(_url_avaliar(auditoria, c, p), {"status": "NAO_APLICAVEL", "justificativa": "Não se aplica à página."})
    assert r.status_code == 302 and r["Location"] == reverse("auditorias:checklist", args=[auditoria.pk])
    assert auditoria.resultados.get(criterio=c, pagina=p).status == ResultadoChecklist.CONFORME


def test_previa_de_severidade(cliente_auditor):
    r = cliente_auditor.get(reverse("auditorias:severidade"), {"impacto": "ALTO", "alcance": "PONTUAL"})
    assert r.json() == {"pontuacao": 3, "nivel": "MEDIA", "rotulo": "Média"}


def test_previa_de_severidade_recusa_parametro_invalido(cliente_auditor):
    r = cliente_auditor.get(reverse("auditorias:severidade"), {"impacto": "ALTO", "alcance": "TOTAL"})
    assert r.status_code == 400 and r.json() == {"erro": "Informe impacto e alcance."}


def test_telas_principais_renderizam(cliente_auditor, auditoria):
    for url in [
        reverse("painel"),
        reverse("projetos:lista"),
        reverse("auditorias:nova"),
        reverse("auditorias:checklist", args=[auditoria.pk]),
    ]:
        assert cliente_auditor.get(url).status_code == 200
