"""Regra de severidade do AcessaSUS (RN03, RF004, ADR-06).

Método de priorização definido pela equipe — não é estabelecido pelas normas
de acessibilidade, que apenas fundamentam o critério violado.

    pontuação = peso(impacto) × peso(alcance)
    faixa: 1–3 BAIXA; 4–6 MEDIA; 8–12 ALTA
    piso por impacto: ALTO → no mínimo MEDIA; CRITICO → ALTA
    nível = maior(faixa, piso)

Este módulo não depende do Django para poder ser testado isoladamente e
alterado em um único lugar caso a validação com auditores (Q01) exija.
"""

from __future__ import annotations

from dataclasses import dataclass

PESO_IMPACTO: dict[str, int] = {"BAIXO": 1, "MEDIO": 2, "ALTO": 3, "CRITICO": 4}
PESO_ALCANCE: dict[str, int] = {"PONTUAL": 1, "PARCIAL": 2, "GLOBAL": 3}

BAIXA, MEDIA, ALTA = "BAIXA", "MEDIA", "ALTA"
ORDEM_NIVEL: dict[str, int] = {BAIXA: 1, MEDIA: 2, ALTA: 3}

PISO_POR_IMPACTO: dict[str, str] = {"ALTO": MEDIA, "CRITICO": ALTA}


@dataclass(frozen=True)
class Severidade:
    pontuacao: int
    nivel: str


def faixa_da_pontuacao(pontuacao: int) -> str:
    if pontuacao <= 3:
        return BAIXA
    if pontuacao <= 6:
        return MEDIA
    return ALTA


def calcular_severidade(impacto: str, alcance: str) -> Severidade:
    """Calcula pontuação e nível. Lança ValueError para parâmetros inválidos."""
    if impacto not in PESO_IMPACTO:
        raise ValueError(f"Impacto inválido: {impacto!r}")
    if alcance not in PESO_ALCANCE:
        raise ValueError(f"Alcance inválido: {alcance!r}")
    pontuacao = PESO_IMPACTO[impacto] * PESO_ALCANCE[alcance]
    nivel = faixa_da_pontuacao(pontuacao)
    piso = PISO_POR_IMPACTO.get(impacto)
    if piso and ORDEM_NIVEL[piso] > ORDEM_NIVEL[nivel]:
        nivel = piso
    return Severidade(pontuacao=pontuacao, nivel=nivel)
