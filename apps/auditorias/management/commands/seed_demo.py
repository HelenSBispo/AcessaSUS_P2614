"""Cria dados sintéticos de demonstração (RN04: nenhum dado real de paciente).

Uso: python manage.py seed_demo [--senha SENHA]
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.auditorias.models import Evidencia, ResultadoChecklist
from apps.auditorias.servicos import DadosAvaliacao, concluir_auditoria, iniciar_auditoria, registrar_avaliacao
from apps.contas.perfis import AUDITOR, GESTOR_TI
from apps.normas.models import BaseNormativa
from apps.projetos.models import Projeto

NC_EXEMPLO = {
    "C02": ("Calendário de datas não recebe foco pelo teclado.", "CRITICO", "PARCIAL"),
    "C05": ("Texto de instruções com contraste 2,6:1 (mínimo 4,5:1).", "MEDIO", "GLOBAL"),
    "C03": ("Links “clique aqui” sem contexto.", "BAIXO", "PARCIAL"),
    "C04": ("Botão “Confirmar agendamento” é imagem sem texto alternativo.", "CRITICO", "PONTUAL"),
}


class Command(BaseCommand):
    help = "Cria usuários de teste e auditorias de exemplo com dados sintéticos."

    def add_arguments(self, parser):
        parser.add_argument("--senha", default=os.environ.get("DEMO_SENHA", "Demo@AcessaSUS2026"))

    @transaction.atomic
    def handle(self, *args, senha, **options):
        User = get_user_model()
        usuarios = {}
        for email, nome, sobrenome, grupo in [
            ("auditora@exemplo.org", "Ana", "Souza", AUDITOR),
            ("gestor@exemplo.org", "Carlos", "Lima", GESTOR_TI),
        ]:
            u, criado = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": nome, "last_name": sobrenome})
            if criado:
                u.set_password(senha)
                u.save()
            u.groups.add(Group.objects.get_or_create(name=grupo)[0])
            usuarios[grupo] = u
        auditora = usuarios[AUDITOR]
        base = BaseNormativa.objects.get(vigente=True)

        projeto, _ = Projeto.objects.get_or_create(
            nome="Agendamento de Exames (exemplo)",
            defaults={
                "esfera_orgao": "Secretaria Municipal de Saúde (fictícia)",
                "url_base": "https://saude.exemplo.gov.br",
                "descricao": "Portal fictício para demonstração.",
                "criado_por": auditora,
            },
        )
        if not projeto.paginas.exists():
            projeto.adicionar_pagina("Página inicial", "https://saude.exemplo.gov.br/")
            projeto.adicionar_pagina("Agendar exame", "https://saude.exemplo.gov.br/exames/agendar")

        if not projeto.auditorias.exists():
            aud = iniciar_auditoria(projeto, projeto.paginas.all(), base, auditora)
            for pagina in projeto.paginas.all():
                for criterio in base.criterios.all():
                    nc = NC_EXEMPLO.get(criterio.codigo) if pagina.nome_rota == "Agendar exame" else None
                    if nc:
                        dados = DadosAvaliacao(
                            status=ResultadoChecklist.NAO_CONFORME,
                            descricao=nc[0],
                            impacto=nc[1],
                            alcance=nc[2],
                            evidencias=[(Evidencia.OBSERVACAO, "Verificado com NVDA + Firefox no ambiente de exemplo.", None)],
                        )
                    elif criterio.codigo == "C08" and pagina.nome_rota == "Página inicial":
                        dados = DadosAvaliacao(
                            status=ResultadoChecklist.NAO_APLICAVEL, justificativa="A página inicial não possui formulário."
                        )
                    else:
                        dados = DadosAvaliacao(status=ResultadoChecklist.CONFORME)
                    registrar_avaliacao(aud, criterio, pagina, auditora, dados)
            concluir_auditoria(aud)

            projeto2, _ = Projeto.objects.get_or_create(
                nome="Portal Saúde Municipal (exemplo)",
                defaults={
                    "esfera_orgao": "Secretaria Municipal de Saúde (fictícia)",
                    "url_base": "https://portal.exemplo.gov.br",
                    "criado_por": auditora,
                },
            )
            if not projeto2.paginas.exists():
                projeto2.adicionar_pagina("Página inicial", "https://portal.exemplo.gov.br/")
            iniciar_auditoria(projeto2, projeto2.paginas.all(), base, auditora)

        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados: auditora@exemplo.org e gestor@exemplo.org."))
