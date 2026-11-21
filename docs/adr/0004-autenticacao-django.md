# ADR-04 — Autenticação e autorização com django.contrib.auth

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RF006, RN05, RNF007

## Contexto

Casos de uso exigem usuário autenticado e permissões diferentes por perfil.

## Decisão

Sessões do Django, grupos Auditor e Gestor de TI, matriz `MATRIZ_PERMISSOES` em `apps/contas/perfis.py`, mixin `PermissaoMixin`, filtro “próprias auditorias”, bloqueio após 5 tentativas por 15 min (cache) e sessão de 30 min.

## Alternativas consideradas

JWT; login gov.br; implementação própria de senhas.

## Consequências

(+) Mecanismo maduro. (−) Bloqueio em cache local não é compartilhado entre processos (débito técnico DT-02).
