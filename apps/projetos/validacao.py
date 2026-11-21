"""Validação de URLs auditadas (RN04 — sem dados pessoais de pacientes)."""

from urllib.parse import parse_qsl, urlparse

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# Parâmetros que costumam carregar identificação pessoal.
PARAMETROS_PESSOAIS = {
    "cpf",
    "cns",
    "cartao_sus",
    "cartaosus",
    "rg",
    "nome",
    "nome_paciente",
    "paciente",
    "email",
    "e-mail",
    "telefone",
    "celular",
    "nascimento",
    "data_nascimento",
    "dtnasc",
    "prontuario",
    "matricula",
    "mae",
    "nome_mae",
}


def validar_url_sem_dado_pessoal(url: str) -> None:
    URLValidator(schemes=["http", "https"])(url)
    consulta = urlparse(url).query
    for nome, _valor in parse_qsl(consulta, keep_blank_values=True):
        if nome.strip().lower() in PARAMETROS_PESSOAIS:
            raise ValidationError(
                "URL recusada: contém parâmetro de identificação pessoal (%(param)s). Cadastre uma página sem dados de pacientes (RN04).",
                code="dado_pessoal",
                params={"param": nome},
            )
