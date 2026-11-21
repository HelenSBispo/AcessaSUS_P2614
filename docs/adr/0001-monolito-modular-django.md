# ADR-01 — Monólito modular em Django

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RST01, RNF002, RNF005

## Contexto

Equipe de cinco estudantes, um semestre, interface que precisa ser acessível e um único contexto de negócio.

## Decisão

Aplicação Django única com apps por subdomínio (`contas`, `projetos`, `normas`, `auditorias`, `relatorios`) e módulo de domínio `severidade`; HTML renderizado no servidor.

## Alternativas consideradas

SPA (React) + API REST; microsserviços.

## Consequências

(+) Menos partes móveis; HTML semântico mais fácil de manter acessível; admin pronto. (−) Escala horizontal limitada; interações ricas exigem JavaScript incremental.
