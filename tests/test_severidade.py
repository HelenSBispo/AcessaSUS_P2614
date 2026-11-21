"""RF004 / RN03 — teste das 12 combinações de impacto × alcance (critério de aceitação 1)."""

import pytest

from apps.severidade.regra import calcular_severidade

# (impacto, alcance, pontuação, nível esperado) — tabela de verificação do P1 v1.1, §8.2
TABELA = [
    ("BAIXO", "PONTUAL", 1, "BAIXA"),
    ("BAIXO", "PARCIAL", 2, "BAIXA"),
    ("BAIXO", "GLOBAL", 3, "BAIXA"),
    ("MEDIO", "PONTUAL", 2, "BAIXA"),
    ("MEDIO", "PARCIAL", 4, "MEDIA"),
    ("MEDIO", "GLOBAL", 6, "MEDIA"),
    ("ALTO", "PONTUAL", 3, "MEDIA"),  # piso por impacto Alto
    ("ALTO", "PARCIAL", 6, "MEDIA"),
    ("ALTO", "GLOBAL", 9, "ALTA"),
    ("CRITICO", "PONTUAL", 4, "ALTA"),  # piso por impacto Crítico
    ("CRITICO", "PARCIAL", 8, "ALTA"),
    ("CRITICO", "GLOBAL", 12, "ALTA"),
]


@pytest.mark.parametrize(("impacto", "alcance", "pontuacao", "nivel"), TABELA)
def test_doze_combinacoes(impacto, alcance, pontuacao, nivel):
    resultado = calcular_severidade(impacto, alcance)
    assert resultado.pontuacao == pontuacao
    assert resultado.nivel == nivel


def test_mesmos_parametros_mesmo_nivel():
    assert calcular_severidade("MEDIO", "GLOBAL") == calcular_severidade("MEDIO", "GLOBAL")


@pytest.mark.parametrize(("impacto", "alcance"), [("", "GLOBAL"), ("MEDIO", ""), ("ENORME", "GLOBAL"), ("BAIXO", "TOTAL")])
def test_parametros_invalidos_nao_geram_nivel(impacto, alcance):
    with pytest.raises(ValueError):
        calcular_severidade(impacto, alcance)


def test_cobertura_da_tabela_completa():
    assert len({(i, a) for i, a, _, _ in TABELA}) == 12
