from django import forms

from .models import Projeto
from .validacao import validar_url_sem_dado_pessoal


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = ["nome", "esfera_orgao", "url_base", "descricao"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3})}


class PaginaForm(forms.Form):
    nome_rota = forms.CharField(label="Nome da rota", max_length=120)
    url = forms.URLField(label="URL", validators=[validar_url_sem_dado_pessoal])
