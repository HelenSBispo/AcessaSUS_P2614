"""Carga do checklist v1.0 (P1 v1.1, Apêndice C) — critérios mantidos como dados (RNF005)."""
import datetime

from django.db import migrations

CRITERIOS = [
    ("C01", "Os níveis de cabeçalho são usados de forma hierárquica?", "Verifique se h1–h6 seguem a estrutura do conteúdo, sem saltos de nível.", "PERCEPTIVEL", "eMAG 1.3; WCAG 1.3.1", "A"),
    ("C02", "Todas as funções estão disponíveis pelo teclado?", "Percorra a página com Tab, Shift+Tab, Enter e Espaço; nenhuma ação pode exigir mouse.", "OPERAVEL", "eMAG 2.1; WCAG 2.1.1", "A"),
    ("C03", "Os links descrevem seu destino de forma clara?", "Leia o texto de cada link fora de contexto; evite “clique aqui”.", "OPERAVEL", "eMAG 3.5; WCAG 2.4.4", "A"),
    ("C04", "Imagens informativas têm alternativa em texto?", "Verifique botões e ícones com função: o leitor de tela deve anunciar a finalidade.", "PERCEPTIVEL", "eMAG 3.6; WCAG 1.1.1", "A"),
    ("C05", "O texto tem contraste mínimo com o fundo?", "Meça com verificador de contraste: ≥ 4,5:1 (texto normal) e ≥ 3:1 (texto grande).", "PERCEPTIVEL", "eMAG 4.1; WCAG 1.4.3", "AA"),
    ("C06", "O elemento com foco é visualmente evidente?", "Navegue com Tab e confirme indicador de foco visível em todos os elementos.", "OPERAVEL", "eMAG 4.4; WCAG 2.4.7", "AA"),
    ("C07", "Os campos de formulário têm rótulos associados?", "Inspecione label/for ou aria-labelledby; o leitor de tela deve anunciar o rótulo.", "COMPREENSIVEL", "eMAG 6.2; WCAG 1.3.1 e 3.3.2", "A"),
    ("C08", "Erros de entrada são identificados e descritos em texto?", "Envie o formulário com erro; a mensagem deve aparecer em texto e ser anunciada.", "COMPREENSIVEL", "eMAG 6.6; WCAG 3.3.1", "A"),
]


def carregar(apps, schema_editor):
    Criterio = apps.get_model("normas", "CriterioNormativo")
    Base = apps.get_model("normas", "BaseNormativa")
    base, _ = Base.objects.get_or_create(
        nome="Checklist AcessaSUS — eMAG 3.1 + WCAG 2.2 A/AA (correspondência ABNT NBR 17225:2025)",
        versao="1.0",
        defaults={"data_publicacao": datetime.date(2026, 11, 21), "vigente": True},
    )
    for codigo, titulo, orientacao, principio, refs, nivel in CRITERIOS:
        criterio, _ = Criterio.objects.update_or_create(
            codigo=codigo,
            defaults={"titulo": titulo, "orientacao_verificacao": orientacao, "principio": principio,
                      "referencias_normativas": refs, "nivel_exigido": nivel},
        )
        base.criterios.add(criterio)


def remover(apps, schema_editor):
    apps.get_model("normas", "BaseNormativa").objects.filter(versao="1.0").delete()


class Migration(migrations.Migration):
    dependencies = [("normas", "0001_initial")]
    operations = [migrations.RunPython(carregar, remover)]
