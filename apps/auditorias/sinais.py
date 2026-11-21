"""Remove do disco o arquivo de uma evidência excluída (ADR-03, descarte em cascata)."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Evidencia


@receiver(post_delete, sender=Evidencia)
def remover_arquivo(sender, instance, **kwargs):
    if instance.arquivo:
        instance.arquivo.delete(save=False)
