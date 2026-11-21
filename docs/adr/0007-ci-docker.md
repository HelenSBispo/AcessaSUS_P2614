# ADR-07 — Integração contínua no GitHub Actions e implantação com Docker Compose

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RNF002, RNF005, RST01

## Contexto

A equipe precisa de verificação automática e demonstração reprodutível.

## Decisão

Workflow com lint (ruff), testes com PostgreSQL e cobertura, acessibilidade (axe-core + Playwright) e build Docker; `docker-compose.yml` com web + db; segredos em `.env` não versionado.

## Alternativas consideradas

Verificação manual; PaaS externo.

## Consequências

(+) Evidência automática a cada PR. (−) Tempo de pipeline.
