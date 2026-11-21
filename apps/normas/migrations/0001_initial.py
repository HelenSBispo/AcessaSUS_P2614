from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="CriterioNormativo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=10, unique=True)),
                ("titulo", models.CharField(max_length=200)),
                ("orientacao_verificacao", models.TextField(verbose_name="orientação de verificação")),
                ("principio", models.CharField(choices=[("PERCEPTIVEL", "Perceptível"), ("OPERAVEL", "Operável"), ("COMPREENSIVEL", "Compreensível"), ("ROBUSTO", "Robusto")], max_length=20)),
                ("referencias_normativas", models.CharField(max_length=200, verbose_name="referências normativas")),
                ("nivel_exigido", models.CharField(max_length=3, verbose_name="nível WCAG")),
            ],
            options={"ordering": ["codigo"], "verbose_name": "critério normativo", "verbose_name_plural": "critérios normativos"},
        ),
        migrations.CreateModel(
            name="BaseNormativa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                ("versao", models.CharField(max_length=20)),
                ("data_publicacao", models.DateField()),
                ("vigente", models.BooleanField(default=False)),
                ("criterios", models.ManyToManyField(related_name="bases", to="normas.criterionormativo")),
            ],
            options={"ordering": ["-vigente", "-data_publicacao"], "verbose_name": "base normativa (versão do checklist)", "verbose_name_plural": "bases normativas (versões do checklist)"},
        ),
    ]
