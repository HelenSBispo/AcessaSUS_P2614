# AcessaSUS

Plataforma web de apoio à **auditoria de acessibilidade digital** (eMAG 3.1, WCAG 2.2 e ABNT NBR 17225:2025) em portais e serviços do SUS.
Projeto Integrador da disciplina **COMP0503 — Engenharia de Software** (DCOMP/UFS, 2026.2) — equipe **P2614**.

| Integrante | |
|---|---|
| Cadmo Octávio José do Nascimento Neto | Guilherme Ferreira Amâncio |
| Gustavo de Jesus Rodrigues | Helen da Silva Bispo |
| Pietro Oliveira Lima | |

## O que o MVP faz

| Requisito | Funcionalidade | Onde no código |
|---|---|---|
| RF006 / UC-06 | Login por e-mail, perfis Auditor e Gestor de TI, bloqueio após 5 tentativas, sessão de 30 min | `apps/contas` |
| RF001 / UC-01 | Cadastro de projetos e páginas; recusa de URL com dado pessoal (RN04) | `apps/projetos` |
| RF002 / UC-02 | Auditoria guiada pelo checklist v1.0 (8 critérios eMAG/WCAG), N/A com justificativa, conclusão só sem pendências | `apps/auditorias`, `apps/normas` |
| RF003 / UC-03 | Não conformidade com evidências (captura PNG/JPG ≤ 5 MB, código, URL ou observação textual — RN02) | `apps/auditorias/servicos.py` |
| RF004 | Severidade por impacto × alcance com piso por impacto (RN03) | `apps/severidade/regra.py` |
| RF005 / UC-04 / UC-05 | Consulta ordenada por severidade e exportação HTML/PDF só de auditoria concluída (RN06) | `apps/relatorios` |

## Como executar (desenvolvimento, SQLite)

Pré-requisitos: Python 3.12+, Git. Para o PDF, as bibliotecas do WeasyPrint (Linux: `libpango-1.0-0 libpangoft2-1.0-0`; Windows/macOS: ver a documentação do WeasyPrint).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # Windows: copy .env.example .env
export $(grep -v '^#' .env | xargs)   # ou defina DJANGO_DEBUG=1 e DJANGO_SECRET_KEY no terminal
python manage.py migrate
python manage.py seed_demo         # usuários e auditorias de exemplo (dados sintéticos)
python manage.py runserver
```

Acesse http://localhost:8000 com os usuários de teste (dados fictícios, sem valor fora do ambiente local):

| Perfil | E-mail | Senha |
|---|---|---|
| Auditor | `auditora@exemplo.org` | `Demo@AcessaSUS2026` |
| Gestor de TI | `gestor@exemplo.org` | `Demo@AcessaSUS2026` |

Administração (critérios, versões do checklist, usuários): `python manage.py createsuperuser` e http://localhost:8000/admin/.

## Como executar com Docker (homologação/demonstração, PostgreSQL)

```bash
cp .env.example .env    # defina DJANGO_SECRET_KEY, POSTGRES_PASSWORD e DJANGO_DEBUG=0
docker compose up --build -d
docker compose exec web python manage.py seed_demo
```

Health check: http://localhost:8000/saude/ → `{"status": "ok", "banco": "ok"}`.

## Testes e qualidade

```bash
ruff check . && ruff format --check .     # lint e formatação
pytest -m "not e2e" --cov                 # unitários e integração
playwright install chromium && pytest -m e2e   # acessibilidade (axe-core, WCAG A/AA)
```

A integração contínua (`.github/workflows/ci.yml`) executa lint, testes com PostgreSQL, verificação de acessibilidade e build da imagem Docker a cada push e pull request na `main`.

## Estrutura

```
config/            configurações (variáveis de ambiente), URLs, WSGI
apps/contas/       autenticação, perfis e matriz de permissões (RN05)
apps/projetos/     Projeto, Página, validação de URL (RN04)
apps/normas/       BaseNormativa, CriterioNormativo, checklist v1.0 (migração de dados)
apps/auditorias/   Auditoria, ResultadoChecklist, NaoConformidade, Evidencia, serviços transacionais
apps/severidade/   regra de severidade pura, sem Django (ADR-06)
apps/relatorios/   consulta por severidade e exportação HTML/PDF (ADR-05)
templates/, static/  interface acessível renderizada no servidor
tests/             pytest (unitários, integração, permissões, e2e de acessibilidade)
docs/adr/          registros de decisão arquitetural
docs/acessibilidade/  procedimento e registros de verificação (RNF002)
```

## Documentação do projeto

Documentos P1, P2 e P3 entregues no SIGAA. Decisões arquiteturais em [`docs/adr`](docs/adr). Convenções de contribuição em [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Uso de inteligência artificial

O código inicial deste repositório foi produzido com apoio de IA generativa (Claude, Anthropic), a partir dos requisitos e modelos do P1/P2 da equipe, e revisado pela equipe. Os commits gerados com apoio de IA contêm a linha `Co-Authored-By: Claude`. Ver o registro de uso de IA no documento P3.
