# Relatório da revisão de testes do P3

## Objetivo e base

Revisão dos testes do MVP AcessaSUS em 22/11/2026, com base em `origin/main` no merge `3e4c4e3`. O recorte prioriza autorização, integridade, severidade, exportação e acessibilidade, conforme o P1 e o P2 v1.1. A [matriz](matriz-rastreabilidade-p3.md) liga os resultados aos requisitos, cenários e decisões já documentados.

O [PR #1](https://github.com/HelenSBispo/AcessaSUS_P2614/pull/1), incorporado à base, acrescentou `test_formato_invalido_nega_exportacao` para verificar HTTP 403 e ausência de emissão. A execução focada `pytest tests/test_relatorios.py --cov=apps.relatorios --cov-report=term-missing` reproduziu 8 aprovações e 46 de 46 linhas em `apps/relatorios/views.py` (100%). Excluindo somente esse caso com `-k "not formato_invalido"`, foram 7 aprovações, 45 de 46 linhas (98%) e a linha 54 ficou descoberta. Na suíte completa da base o arquivo já tinha 46 de 46 linhas executadas.

## Diagnóstico anterior às alterações

| Prioridade | Requisito e módulo | Testes existentes e comportamento coberto | Lacuna, risco e verificação proposta |
| --- | --- | --- | --- |
| Alta | RF006/RN05 e RF005/RN06, views de auditoria e relatórios | `test_matriz_de_permissoes`, login/logout, bloqueio, negação de leitura cruzada e exportação por Auditor responsável ou Gestor | A leitura negada não demonstra a proteção das operações de escrita e emissão. Exercitar o POST de registro de NC por outro Auditor e por Gestor, e o POST de exportação por Auditor de outra auditoria. Verificar 403 e ausência de gravação |
| Alta | RF003/RN02/RN04, formulário e serviço de auditorias | Observação isolada, captura válida e inválida, ausência de evidência, exclusão em cascata e rollback do resultado | URL e trecho de código válidos não tinham verificação de associação. A URL restrita podia passar despercebida nos testes de evidência. Exercitar os dois tipos isoladamente, recusar URL com parâmetro pessoal e comprovar rollback de resultado, NC e evidência |
| Alta | RF005/RN06, views e template de relatórios | Consulta, ordem e filtro no modelo, exportação HTML/PDF, formato inválido e falha simulada de PDF | O HTML só verificava se uma falha aparecia antes da seção de resultados. Os bloqueios verificavam apenas o redirecionamento e a ausência de emissão. Verificar a ordem efetiva no HTML, a ausência de oferta de exportação e a comunicação de pendências e falhas |
| Alta | RNF002, templates e Playwright | Dois testes com axe em nove telas. O registro histórico na base anotava dez, com ajuste para nove na branch remota `docs/corrigir-registro-a11y` | O relatório HTML constava do escopo, mas estava fora da execução automática. Baixar e abrir o documento no Chromium, confirmar sua identidade e executar axe |
| Acompanhamento | RF004/RN03, função de severidade, modelo e prévia | As 12 combinações com pontuação e nível, pisos, entradas inválidas, determinismo, prévia HTTP, persistência e ordenação | Cobertura comportamental adequada para o cálculo. O teste de cardinalidade auxilia a detectar um conjunto incompleto de dados, mas a verificação da regra vem das assertions parametrizadas. A ordem no HTML é reforçada na linha de RF005 |

A revisão também leu as fixtures compartilhadas, os testes de projetos e os fluxos de auditoria. Os testes de projeto já cobrem criação, campos obrigatórios, duplicidade e recusa de URL com parâmetro pessoal. Os testes de auditoria já protegem a conclusão com pendências e a edição após conclusão.

## Alterações e defeitos

- **Seis casos adicionais de integração.** Dois aceitam e vinculam evidências por URL ou trecho de código, um recusa URL com parâmetro pessoal e três verificam POSTs proibidos. Cada caso verifica o efeito esperado no banco.
- **Assertions reforçadas.** O rollback de RN02 comprova a ausência das três gravações. A exportação HTML verifica a ordem Alta → Média → Baixa com desempate por pontuação. Os cenários de auditoria em andamento e falha de renderização verificam o destino e a mensagem exibida.
- **E2E ampliado.** O teste existente do Gestor abre o HTML baixado via fluxo real e verifica o documento com axe. O caso já existente de formato inválido segue como evidência do PR #1.

As verificações acrescentadas passaram com a implementação existente. A única falha inicial observada foi ambiental. No Windows, o teste de PDF recebeu 302 porque o WeasyPrint não conseguiu carregar as DLLs nativas. Foi necessário provisionar Pango, Fontconfig, HarfBuzz e GLib e adequar os nomes de DLL que o WeasyPrint busca no ambiente virtual temporário. O teste de PDF passou após o ajuste. A contribuição altera testes e documentação.

## Resultados reproduzíveis

Ambiente local Windows, Python 3.12.14, Django 5.2.19, pytest 9.2.0, Ruff 0.17.6, WeasyPrint 70.0 e Chromium 159 via Playwright 1.65.2. Dados e credenciais de teste sintéticos. A CI usa Ubuntu e PostgreSQL 16 para os testes de integração.

| Comando | Base `3e4c4e3` | Branch da revisão |
| --- | --- | --- |
| `ruff check .` e `ruff format --check .` | Aprovados, 68 arquivos formatados | Aprovados, 68 arquivos formatados |
| `pytest -m "not e2e" --cov --cov-report=term-missing` em SQLite | 64 aprovados, 2 desselecionados. 719/769 linhas (93,498%, exibido como 93% pelo Coverage.py) | 70 aprovados, 2 desselecionados. 721/769 linhas (93,758%, exibido como 94%) |
| `playwright install chromium` e `pytest -m e2e` em SQLite | 2 aprovados, 64 desselecionados. Nove varreduras, zero violações detectadas | 2 aprovados, 70 desselecionados. Dez varreduras, zero violações detectadas |
| `python manage.py makemigrations --check --dry-run --settings=config.settings_test` em PostgreSQL 16.16 | — | Nenhuma alteração detectada |
| `pytest -m "not e2e" --cov --cov-report=term-missing` em PostgreSQL 16.16 | — | 70 aprovados, 2 desselecionados. 721/769 linhas (93,758%, exibido como 94%) |

A cobertura é de linhas de `apps/` com as exclusões de `pyproject.toml`. Para repetir a execução no PostgreSQL, configure as variáveis `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e `POSTGRES_PORT` para uma instância dedicada a testes. O workflow de CI define o ambiente Linux de referência para a geração de PDF. Foram observados avisos de depreciação do Django/pytest e de ausência de `staticfiles/` durante a execução local.

## Evidências e pendências do P3

| Seção | Evidência aproveitável |
| --- | --- |
| 7 — Qualidade do código | Diagnóstico e diff localizado. Assertions verificam estado, conteúdo e efeitos observáveis |
| 8 — Testes | Comandos e resultados, validações de RF003/RF004/RF005/RF006 e varreduras automatizadas de RNF002 |
| 9 — CI | Jobs e artefatos `resultados-testes` no workflow. Vincular a execução do PR após publicação |
| 12 — Rastreabilidade | [Matriz](matriz-rastreabilidade-p3.md) com origem, cenário, ADR, código, teste e status |
| 13 — Riscos e débitos | Roteiro manual de RNF002, carga do RNF003, ciclo de vida de arquivos em falhas e comportamento temporal das sessões |
| 15 — Participação | Branch `test/auditoria-cobertura-rastreabilidade-p3` e commit de testes `86064ef`. Vincular a revisão de outro integrante ao PR conforme o CONTRIBUTING |

Restam as verificações manuais de teclado, leitor de tela, zoom/reflow e contraste, a avaliação com usuários e a medição concorrente do RNF003. A emissão isolada de PDF abaixo de três segundos é um indicador funcional local. A qualidade e equivalência do conteúdo do PDF em relação ao HTML exigem inspeção específica. Os testes de parâmetros restritos em URLs demonstram um recorte de RN04. Para a revisão da equipe, registrar no README o uso de Codex na auditoria, nos testes e na rastreabilidade, em continuidade à declaração de uso de IA existente.

## Segunda rodada de revisão da cobertura

Base desta rodada: `304c45f`. O commit `359ccb8` acrescenta 19 casos em quatro arquivos existentes. A priorização considerou o risco funcional, inclusive em módulos que já tinham 100% das linhas. Os comandos, o escopo de `apps/` e as exclusões oficiais foram mantidos. Para a análise de ramificações, foi acrescentado apenas `--cov-branch` à invocação do pytest.

| Prioridade | Diagnóstico na base | Evidência acrescentada |
| --- | --- | --- |
| Alta | RF006/RN05/RNF007. Login coberto por linhas, com lacunas na expiração do bloqueio, na renovação por atividade e no escopo do painel | Três casos. Cache e sessão reais com relógios controlados verificam liberação após 15 minutos e expiração após 30 minutos de inatividade. O painel retorna auditorias de todos os responsáveis para o Gestor e apenas as próprias para o Auditor |
| Alta | RF002/RN01 e RF003/RN02. Caminhos de escopo, validação no serviço e edição de NC existente sem exercício | Quatorze casos em auditorias. Recusa início sem critérios ou com páginas inválidas, impede registros fora do escopo, verifica validação do serviço e bloqueio HTTP após conclusão. Edita NC preservando o arquivo e recalculando a severidade. Uma falha injetada na escrita do arquivo verifica que o banco reverte os dados novos e mantém a evidência original |
| Média | RF001/UC-01. Duplicidade já testada no modelo, com lacuna na resposta ao usuário | Um caso verifica o detalhe do projeto, o erro de duplicidade no formulário e a quantidade de páginas |
| Média | RF004/UC-04. Ordenação e severidade já testadas, com lacuna na combinação dos filtros de página e princípio | Um caso de consulta valida o resultado exato e a resposta sem apontamentos quando o princípio não corresponde |

### Linhas identificadas e classificação das pendências

| Arquivo | Linhas adicionais cobertas | Linhas que continuam descobertas e motivo |
| --- | --- | --- |
| `apps/auditorias/forms.py` | 69 | Nenhuma |
| `apps/auditorias/models.py` | 74, 76, 109, 111, 208 | 30, 37, 105, 116–120, 146, 179, 212. Representações, acesso auxiliar a status/detalhes e descarte direto. A reversão de NC e a remoção em cascata já têm teste. A linha 58 protege a chamada direta a `Auditoria.concluir()`. O fluxo público com pendências já é exercitado pelo serviço e pela view |
| `apps/auditorias/servicos.py` | 16, 18, 20, 41, 43, 51, 53 | Nenhuma |
| `apps/auditorias/views.py` | 67–68, 72, 142, 144, 151–152, 204–205 | 85 trata a checagem do responsável após a checagem de visibilidade. 157–158 acrescentam uma validação do serviço ao formulário quando ela ocorre depois de o formulário ter sido aceito. Os perfis do MVP e os caminhos de erro verificáveis pelo fluxo regular foram priorizados |
| `apps/contas/perfis.py` | — | 38 e 63 são acessos administrativos de superusuário, fora dos perfis do MVP |
| `apps/normas/models.py` | — | 27 e 51 são representação e listagem auxiliar |
| `apps/projetos/models.py`, `apps/projetos/views.py` | 20, 43 e 47–48, 58–59, respectivamente | Nenhuma |
| `apps/relatorios/models.py` | — | 23 é representação textual do registro de emissão |

As dez ramificações ainda abertas concentram-se em base sem versão vigente, guarda de pendências em método direto, detalhes auxiliares, descarte sem arquivo, caminhos alternativos de formulário e autorização administrativa. A falha de armazenamento testada ocorre durante o envio de uma nova captura e valida rollback do banco. Falhas posteriores a uma escrita física, concorrência e consistência entre banco e armazenamento continuam pendentes. O teste de bloqueio usa o cache local configurado e não verifica compartilhamento do bloqueio entre processos. O caminho de falha de renderização de relatório já tinha um teste e foi preservado.

### Resultados da segunda rodada

| Métrica em SQLite | Inicial | Final |
| --- | --- | --- |
| Testes sem E2E | 70 aprovados | 89 aprovados, 19 adicionais |
| Linhas de `apps/` | 721/769 (93,758%) | 749/769 (97,399%), 28 adicionais |
| Ramificações, execução com `--cov-branch` | 121/148 (81,757%) | 138/148 (93,243%), 17 adicionais |
| Métrica combinada de linhas e ramificações | 842/917 (91,821%) | 887/917 (96,728%) |

Também passaram 89 testes em PostgreSQL 16.16, com 749/769 linhas cobertas e nenhuma alteração de migrações detectada. Passaram os dois E2E em SQLite, com dez varreduras axe e zero violações detectadas. `ruff check .` e `ruff format --check .` passaram. Os novos testes passaram com o código de produção existente. O diff desta rodada contém apenas testes e a atualização destes documentos. A branch permanece local, preparada para revisão.
