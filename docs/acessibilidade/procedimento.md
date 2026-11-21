# Verificação de acessibilidade da própria interface (RNF002)

Procedimento definido no P1 v1.1, §9.2 (inspirado na WCAG-EM do W3C).

| Etapa | Como | Critério |
|---|---|---|
| 1. Escopo | Login, painel, projetos, novo projeto, detalhe do projeto, nova auditoria, checklist, avaliar critério, consulta/relatório, relatório HTML | Todas as telas do MVP |
| 2. Automática | `pytest -m e2e` (axe-core, tags wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa) na CI | 0 violações; falha bloqueia o merge |
| 3. Teclado | Fluxo principal só com teclado | Todas as ações alcançáveis; foco visível |
| 4. Leitor de tela | NVDA + Firefox | Rótulos, erros e severidade anunciados |
| 5. Zoom/reflow | 200% e 320 px | Sem perda de conteúdo |
| 6. Contraste | Tokens de cor de `static/css/app.css` | ≥ 4,5:1 (texto) e ≥ 3:1 (componentes) |
| 7. Registro | `registro-sprint-N.md` | Reprovação vira issue `a11y` |
