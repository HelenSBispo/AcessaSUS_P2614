# ADR-02 — Persistência relacional em PostgreSQL via ORM

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RN02, R05, RNF004

## Contexto

O registro de uma não conformidade envolve várias tabelas que precisam ser gravadas juntas.

## Decisão

PostgreSQL 16 em homologação e CI; SQLite só no desenvolvimento local. Registro de NC em `transaction.atomic()` (`apps/auditorias/servicos.py`).

## Alternativas consideradas

SQLite em todos os ambientes; banco de documentos.

## Consequências

(+) Transações ACID, restrições de unicidade (resultado por critério × página; URL por projeto). (−) Serviço de banco extra no ambiente de demonstração.
