from django.contrib import admin

from .models import Auditoria, Evidencia, NaoConformidade, ResultadoChecklist

admin.site.register(Auditoria)
admin.site.register(ResultadoChecklist)
admin.site.register(NaoConformidade)
admin.site.register(Evidencia)
