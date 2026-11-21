import pytest
from django.contrib.auth.models import Group
from django.core.cache import cache

from apps.auditorias.servicos import iniciar_auditoria
from apps.contas.perfis import AUDITOR, GESTOR_TI
from apps.normas.models import BaseNormativa
from apps.projetos.models import Projeto

SENHA = "Senha@Teste123"


@pytest.fixture(autouse=True)
def limpar_cache():
    cache.clear()
    yield
    cache.clear()


def _usuario(django_user_model, email, grupo=None):
    u = django_user_model.objects.create_user(username=email, email=email, password=SENHA, first_name="Teste")
    if grupo:
        u.groups.add(Group.objects.get(name=grupo))
    return u


@pytest.fixture
def auditor(db, django_user_model):
    return _usuario(django_user_model, "auditor@exemplo.org", AUDITOR)


@pytest.fixture
def outro_auditor(db, django_user_model):
    return _usuario(django_user_model, "auditor2@exemplo.org", AUDITOR)


@pytest.fixture
def gestor(db, django_user_model):
    return _usuario(django_user_model, "gestor@exemplo.org", GESTOR_TI)


@pytest.fixture
def sem_perfil(db, django_user_model):
    return _usuario(django_user_model, "semperfil@exemplo.org")


@pytest.fixture
def base(db):
    return BaseNormativa.objects.get(vigente=True)


@pytest.fixture
def projeto(auditor):
    p = Projeto.objects.create(nome="Portal de exemplo", esfera_orgao="SMS fictícia", url_base="https://exemplo.gov.br", criado_por=auditor)
    p.adicionar_pagina("Inicial", "https://exemplo.gov.br/")
    p.adicionar_pagina("Agendar", "https://exemplo.gov.br/agendar")
    return p


@pytest.fixture
def auditoria(projeto, base, auditor):
    return iniciar_auditoria(projeto, projeto.paginas.all(), base, auditor)


@pytest.fixture
def cliente_auditor(client, auditor):
    client.force_login(auditor)
    return client


@pytest.fixture
def cliente_gestor(client, gestor):
    client.force_login(gestor)
    return client
