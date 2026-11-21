"""Casos de uso de auditoria (UC-02, UC-03) com integridade transacional (ADR-02, R05)."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Auditoria, Evidencia, NaoConformidade, ResultadoChecklist


def iniciar_auditoria(projeto, paginas, base, usuario) -> Auditoria:
    paginas = list(paginas)
    if not paginas:
        raise ValidationError("Selecione ao menos uma página.")
    if any(p.projeto_id != projeto.pk for p in paginas):
        raise ValidationError("Todas as páginas devem pertencer ao projeto selecionado.")
    if not base.criterios.exists():
        raise ValidationError("A base normativa selecionada não possui critérios.")
    with transaction.atomic():
        auditoria = Auditoria.objects.create(projeto=projeto, auditor=usuario, base=base)
        auditoria.paginas.set(paginas)
    return auditoria


@dataclass
class DadosAvaliacao:
    status: str
    justificativa: str = ""
    descricao: str = ""
    impacto: str = ""
    alcance: str = ""
    evidencias: list[tuple[str, str, object | None]] = field(default_factory=list)  # (tipo, conteudo, arquivo)


def registrar_avaliacao(auditoria: Auditoria, criterio, pagina, usuario, dados: DadosAvaliacao) -> ResultadoChecklist:
    """Registra o resultado de um critério em uma página.

    Para Não Conforme, cria/atualiza a não conformidade e suas evidências na mesma
    transação; se a RN02 não for atendida, nada é gravado.
    """
    if auditoria.concluida:
        raise ValidationError("A auditoria já foi concluída e não pode ser alterada.")
    if not auditoria.base.criterios.filter(pk=criterio.pk).exists():
        raise ValidationError("O critério não pertence à base normativa desta auditoria.")
    if not auditoria.paginas.filter(pk=pagina.pk).exists():
        raise ValidationError("A página não faz parte desta auditoria.")

    with transaction.atomic():
        resultado = ResultadoChecklist.objects.filter(auditoria=auditoria, criterio=criterio, pagina=pagina).first()
        if resultado is None:
            resultado = ResultadoChecklist(auditoria=auditoria, criterio=criterio, pagina=pagina)
        resultado.registrar_avaliacao(dados.status, dados.justificativa)
        resultado.registrado_por = usuario
        resultado.save()

        nc_existente = NaoConformidade.objects.filter(resultado=resultado).first()
        if dados.status != ResultadoChecklist.NAO_CONFORME:
            if nc_existente:
                nc_existente.delete()  # evidências e arquivos removidos em cascata
            return resultado

        nc = nc_existente or NaoConformidade(resultado=resultado)
        nc.definir_descricao(dados.descricao)
        if not nc.descricao_falha:
            raise ValidationError("Descreva a falha encontrada.", code="descricao")
        if not dados.impacto or not dados.alcance:
            raise ValidationError("Informe o impacto e o alcance para calcular a severidade.", code="parametros")
        nc.informar_parametros(dados.impacto, dados.alcance)
        nc.save()
        for tipo, conteudo, arquivo in dados.evidencias:
            Evidencia.objects.create(nao_conformidade=nc, tipo=tipo, conteudo=conteudo or "", arquivo=arquivo or "")
        if not nc.verificar_completude():
            raise ValidationError("Registre ao menos uma evidência (a observação textual é suficiente — RN02).", code="evidencia")
    return resultado


def concluir_auditoria(auditoria: Auditoria) -> list[str]:
    """Conclui a auditoria ou devolve a lista de pendências (UC-02, passo 9)."""
    pendencias = auditoria.verificar_pendencias()
    if pendencias:
        return pendencias
    auditoria.concluir()
    return []
