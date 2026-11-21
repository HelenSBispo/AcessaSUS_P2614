from .perfis import perfil_de, possui_permissao


def perfil(request):
    usuario = getattr(request, "user", None)
    return {
        "perfil_usuario": perfil_de(usuario) if usuario else None,
        "pode_editar_projeto": bool(usuario) and possui_permissao(usuario, "projeto.editar"),
        "pode_executar_auditoria": bool(usuario) and possui_permissao(usuario, "auditoria.executar"),
    }
