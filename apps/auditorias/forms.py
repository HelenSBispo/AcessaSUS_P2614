from django import forms
from django.conf import settings

from apps.normas.models import BaseNormativa
from apps.projetos.models import Pagina, Projeto
from apps.projetos.validacao import validar_url_sem_dado_pessoal

from .models import Evidencia, NaoConformidade, ResultadoChecklist
from .servicos import DadosAvaliacao

ASSINATURAS = {"png": [b"\x89PNG\r\n\x1a\n"], "jpg": [b"\xff\xd8\xff"], "jpeg": [b"\xff\xd8\xff"]}


def validar_captura(arquivo) -> None:
    """Valida extensão, assinatura binária e tamanho (ADR-03, UC-03 passo 5a)."""
    extensao = arquivo.name.rsplit(".", 1)[-1].lower() if "." in arquivo.name else ""
    if extensao not in settings.EVIDENCIA_FORMATOS:
        raise forms.ValidationError("Formato não aceito. Envie PNG ou JPG.")
    if arquivo.size > settings.EVIDENCIA_TAMANHO_MAXIMO:
        raise forms.ValidationError("Arquivo acima de 5 MB.")
    cabecalho = arquivo.read(8)
    arquivo.seek(0)
    if not any(cabecalho.startswith(a) for a in ASSINATURAS[extensao]):
        raise forms.ValidationError("O conteúdo do arquivo não corresponde a uma imagem PNG ou JPG.")


class NovaAuditoriaForm(forms.Form):
    projeto = forms.ModelChoiceField(queryset=Projeto.objects.all(), label="Projeto")
    paginas = forms.ModelMultipleChoiceField(
        queryset=Pagina.objects.none(), widget=forms.CheckboxSelectMultiple, label="Páginas abrangidas"
    )
    base = forms.ModelChoiceField(queryset=BaseNormativa.objects.all(), label="Base normativa (versão do checklist)")

    def __init__(self, *args, projeto=None, **kwargs):
        super().__init__(*args, **kwargs)
        vigente = BaseNormativa.objects.filter(vigente=True).first()
        if vigente:
            self.fields["base"].initial = vigente
        projeto_id = self.data.get("projeto") or (projeto.pk if projeto else None)
        if projeto_id:
            self.fields["paginas"].queryset = Pagina.objects.filter(projeto_id=projeto_id)
            self.fields["projeto"].initial = projeto_id


class AvaliacaoForm(forms.Form):
    status = forms.ChoiceField(choices=ResultadoChecklist.STATUS, widget=forms.RadioSelect, label="Resultado")
    justificativa = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Justificativa do Não Aplicável")
    descricao = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Descrição da falha")
    impacto = forms.ChoiceField(required=False, choices=[("", "Selecione")] + NaoConformidade.IMPACTOS, label="Impacto no usuário")
    alcance = forms.ChoiceField(required=False, choices=[("", "Selecione")] + NaoConformidade.ALCANCES, label="Alcance da barreira")
    observacao = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Observação textual")
    trecho_codigo = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2, "spellcheck": "false"}), label="Trecho de código"
    )
    url_evidencia = forms.URLField(required=False, label="URL da evidência", validators=[validar_url_sem_dado_pessoal])
    captura = forms.FileField(required=False, label="Captura de tela (PNG ou JPG, até 5 MB)", validators=[validar_captura])

    def __init__(self, *args, evidencias_existentes: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.evidencias_existentes = evidencias_existentes

    def clean(self):
        dados = super().clean()
        status = dados.get("status")
        if status == ResultadoChecklist.NAO_APLICAVEL and not dados.get("justificativa", "").strip():
            self.add_error("justificativa", "Obrigatória para o resultado Não Aplicável.")
        if status == ResultadoChecklist.NAO_CONFORME:
            if not dados.get("descricao", "").strip():
                self.add_error("descricao", "Descreva a falha encontrada.")
            if not dados.get("impacto"):
                self.add_error("impacto", "Informe o impacto no usuário.")
            if not dados.get("alcance"):
                self.add_error("alcance", "Informe o alcance da barreira.")
            novas = [dados.get("observacao"), dados.get("trecho_codigo"), dados.get("url_evidencia"), dados.get("captura")]
            if not any(novas) and self.evidencias_existentes == 0 and "captura" not in self.errors:
                self.add_error(None, "Registre ao menos uma evidência. A observação textual é suficiente (RN02).")
        return dados

    def para_dados(self) -> DadosAvaliacao:
        d = self.cleaned_data
        evidencias = []
        if d.get("observacao", "").strip():
            evidencias.append((Evidencia.OBSERVACAO, d["observacao"].strip(), None))
        if d.get("trecho_codigo", "").strip():
            evidencias.append((Evidencia.CODIGO, d["trecho_codigo"].strip(), None))
        if d.get("url_evidencia"):
            evidencias.append((Evidencia.URL, d["url_evidencia"], None))
        if d.get("captura"):
            evidencias.append((Evidencia.CAPTURA, "", d["captura"]))
        return DadosAvaliacao(
            status=d["status"],
            justificativa=d.get("justificativa", ""),
            descricao=d.get("descricao", ""),
            impacto=d.get("impacto", ""),
            alcance=d.get("alcance", ""),
            evidencias=evidencias,
        )
