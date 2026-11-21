# Como contribuir

## Branches e pull requests

- `main` é protegida: só recebe código por **pull request** revisado por pelo menos 1 integrante e com a CI verde.
- Crie uma branch por item do backlog: `feat/<assunto>`, `fix/<assunto>`, `docs/<assunto>`, `test/<assunto>`, `refactor/<assunto>`.
- Pull request: título no padrão de commits, descrição com o item de backlog (PBxx/issue), requisitos afetados (RFxxx/RNxx) e como testar.
- Conflitos: atualize a branch com `git pull --rebase origin main`, resolva localmente, rode `pytest` e envie de novo.

## Commits (Conventional Commits)

```
<tipo>(<escopo>): <descrição no imperativo>

feat(auditorias): registrar não conformidade com evidências (RF003)
fix(projetos): recusar URL com parâmetro cns (RN04)
test(severidade): cobrir as 12 combinações (RF004)
```

Tipos: `feat`, `fix`, `test`, `refactor`, `docs`, `ci`, `build`, `chore`, `style`.

## Antes de abrir o PR

```bash
ruff check . && ruff format --check .
pytest -m "not e2e"
```

## Definition of Done

Implementado, integrado à `main` por PR revisado, testes automatizados passando na CI, critérios de aceitação atendidos e sem violações de acessibilidade A/AA nas telas alteradas.

## Versões

Tags seguem Semantic Versioning: `v0.3.0` = incremento do P3; `v1.0.0` = entrega final (P4).
