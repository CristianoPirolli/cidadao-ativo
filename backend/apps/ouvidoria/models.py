"""Modelos da ouvidoria municipal."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class OuvidoriaMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='ouvidoria_messages', db_index=True
    )
    municipio_ibge_id = models.IntegerField(db_index=True)
    municipio_nome = models.CharField(max_length=100)
    municipio_uf = models.CharField(max_length=2)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='ouvidoria_moderations', db_column='moderated_by'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ouvidoria_message'
        verbose_name = 'mensagem da ouvidoria'
        verbose_name_plural = 'mensagens da ouvidoria'

    def __str__(self):
        return f'<OuvidoriaMessage {self.id} municipio={self.municipio_ibge_id}>'
