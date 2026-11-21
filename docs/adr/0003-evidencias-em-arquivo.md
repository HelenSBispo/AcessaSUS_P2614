# ADR-03 — Evidências em arquivos com metadados no banco

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RF003, RN02, RN04, R03

## Contexto

Capturas de tela podem ser grandes; evidências textuais não precisam de arquivo.

## Decisão

`FileField` em `MEDIA_ROOT` (volume Docker); validação de extensão, assinatura binária (PNG/JPG) e tamanho ≤ 5 MB; arquivo removido por sinal `post_delete`.

## Alternativas consideradas

BLOB no banco; armazenamento em nuvem (S3).

## Consequências

(+) Simples e barato. (−) Backup precisa incluir o volume; arquivos não são servidos com `DEBUG=0` (débito técnico).
