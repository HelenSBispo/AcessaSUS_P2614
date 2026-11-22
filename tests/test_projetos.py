"""RF001 / UC-01 / RN04."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.projetos.models import Projeto
from apps.projetos.validacao import validar_url_sem_dado_pessoal


@pytest.mark.parametrize(
    "url", ["https://exemplo.gov.br/exames?cpf=00000000000", "https://x.gov.br/r?CNS=1", "https://x.gov.br/?nome_paciente=a"]
)
def test_url_com_dado_pessoal_e_recusada(url):
    with pytest.raises(ValidationError):
        validar_url_sem_dado_pessoal(url)


def test_url_publica_e_aceita():
    validar_url_sem_dado_pessoal("https://exemplo.gov.br/agendamento?etapa=2")


def test_cadastrar_projeto_e_pagina(cliente_auditor):
    r = cliente_auditor.post(reverse("projetos:novo"), {"nome": "Portal X", "esfera_orgao": "SMS", "url_base": "https://x.gov.br"})
    assert r.status_code == 302
    projeto = Projeto.objects.get(nome="Portal X")
    r = cliente_auditor.post(reverse("projetos:detalhe", args=[projeto.pk]), {"nome_rota": "Inicial", "url": "https://x.gov.br/"})
    assert r.status_code == 302
    assert projeto.paginas.count() == 1


def test_campos_obrigatorios(cliente_auditor):
    r = cliente_auditor.post(reverse("projetos:novo"), {"nome": "", "esfera_orgao": "", "url_base": ""})
    assert r.status_code == 200
    assert not Projeto.objects.exists()
    assert "obrigatório" in r.content.decode()


def test_pagina_com_cpf_recusada_na_tela(cliente_auditor, projeto):
    r = cliente_auditor.post(
        reverse("projetos:detalhe", args=[projeto.pk]), {"nome_rota": "Exame", "url": "https://exemplo.gov.br/e?cpf=1"}
    )
    assert r.status_code == 400
    assert "RN04" in r.content.decode()
    assert projeto.paginas.count() == 2


def test_pagina_duplicada_recusada(projeto):
    with pytest.raises(ValidationError):
        projeto.adicionar_pagina("Repetida", "https://exemplo.gov.br/")


def test_pagina_duplicada_exibe_erro_no_detalhe(cliente_auditor, projeto):
    url = reverse("projetos:detalhe", args=[projeto.pk])
    r = cliente_auditor.get(url)
    assert r.status_code == 200 and r.context["projeto"] == projeto
    r = cliente_auditor.post(url, {"nome_rota": "Repetida", "url": "https://exemplo.gov.br/"})
    assert r.status_code == 400
    assert "Esta URL já está cadastrada neste projeto." in r.context["form"].errors["url"]
    assert projeto.paginas.count() == 2
