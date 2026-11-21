# ADR-05 — Relatório em template HTML único e PDF com WeasyPrint (síncrono)

- **Status:** Aceita — implementada
- **Data:** 2026-11-21
- **Drivers/ASR:** RF005, RNF003, RN06

## Contexto

HTML e PDF precisam ter o mesmo conteúdo e ordenação.

## Decisão

Template `relatorios/documento.html` gera o HTML; o PDF é produzido do mesmo HTML com WeasyPrint na própria requisição; a emissão (`Relatorio`) só é registrada após sucesso e guarda `duracao_ms`.

## Alternativas consideradas

ReportLab; navegador headless; fila assíncrona (Celery).

## Consequências

(+) Fonte única. (−) Geração síncrona é ponto sensível do RNF003; depende de Pango no sistema.
