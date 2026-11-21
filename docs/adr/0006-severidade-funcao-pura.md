# ADR-06 — Cálculo de severidade em função de domínio pura

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RN03, RF004, RNF005

## Contexto

A regra pode mudar após validação com auditores (Q01).

## Decisão

`calcular_severidade(impacto, alcance)` em `apps/severidade/regra.py`, sem Django; `NaoConformidade.calcular_severidade()` delega a ela.

## Alternativas consideradas

Cálculo na view/template; campo calculado no banco.

## Consequências

(+) Teste parametrizado com as 12 combinações. (−) Valores gravados precisam ser recalculados se a regra mudar.
