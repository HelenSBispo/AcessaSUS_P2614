from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache

MENSAGEM_GENERICA = "E-mail ou senha inválidos. Verifique os dados e tente novamente."


def _chave(identificador: str) -> str:
    return f"login-tentativas:{identificador.strip().lower()}"


class EntrarForm(AuthenticationForm):
    """Login por e-mail (usado como username) com bloqueio após tentativas (RNF007)."""

    username = forms.CharField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))
    error_messages = {
        "invalid_login": MENSAGEM_GENERICA,
        "inactive": MENSAGEM_GENERICA,
        "bloqueado": "Acesso bloqueado temporariamente por excesso de tentativas. Tente novamente em 15 minutos.",
    }

    def clean(self):
        identificador = self.data.get("username", "")
        chave = _chave(identificador)
        tentativas = cache.get(chave, 0)
        if tentativas >= settings.LOGIN_MAX_TENTATIVAS:
            raise forms.ValidationError(self.error_messages["bloqueado"], code="bloqueado")
        try:
            dados = super().clean()
        except forms.ValidationError:
            cache.set(chave, tentativas + 1, settings.LOGIN_BLOQUEIO_SEGUNDOS)
            raise
        cache.delete(chave)
        return dados
