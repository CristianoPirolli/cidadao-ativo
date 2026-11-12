from django.contrib import admin

from apps.ouvidoria.models import OuvidoriaMessage


@admin.register(OuvidoriaMessage)
class OuvidoriaMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'municipio_nome', 'is_active', 'created_at')
    list_filter = ('is_active', 'municipio_uf')
    ordering = ('-created_at',)
