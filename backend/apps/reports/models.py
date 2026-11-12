"""Modelos de chamados (denúncias), histórico, votos e notificações."""
import os

from django.conf import settings
from django.db import models
from django.utils import timezone


class ReportStatus(models.TextChoices):
    OPEN = 'aberto', 'Aberto'
    VIEWED = 'visualizado', 'Visualizado'
    IN_PROGRESS = 'em_andamento', 'Em Andamento'
    RESOLVED = 'resolvido', 'Resolvido'
    REJECTED = 'rejeitado', 'Rejeitado'
    # Status legados mantidos por compatibilidade com dados antigos
    IN_EXECUTION = 'em_execucao', 'Em Execução'
    COMPLETED = 'concluido', 'Concluído'
    EVALUATED = 'avaliado', 'Avaliado'


class ReportCategory(models.TextChoices):
    LIGHTING = 'iluminacao', 'Iluminação'
    ROADS = 'via_publica', 'Vias e Calçadas'
    WATER_SEWAGE = 'agua_esgoto', 'Água e Esgoto'
    CLEANING = 'limpeza', 'Limpeza'
    OTHER = 'outros', 'Outros'


class Report(models.Model):
    title = models.CharField(max_length=140, db_index=True)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=ReportCategory.choices, db_index=True)
    lat = models.FloatField()
    lng = models.FloatField()
    image_path = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=ReportStatus.choices, default=ReportStatus.OPEN, db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    viewed_at = models.DateTimeField(null=True, blank=True)

    # Conclusão
    completion_image = models.CharField(max_length=255, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Avaliação
    rating = models.IntegerField(null=True, blank=True)
    citizen_feedback = models.TextField(null=True, blank=True)
    evaluation_image = models.CharField(max_length=255, null=True, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    # Município
    municipio_ibge_id = models.IntegerField(null=True, blank=True, db_index=True)
    municipio_nome = models.CharField(max_length=100, null=True, blank=True)
    municipio_uf = models.CharField(max_length=2, null=True, blank=True)

    # Relacionamentos
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reports_created'
    )
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reports_assigned',
        db_column='assigned_to'
    )

    class Meta:
        db_table = 'report'
        verbose_name = 'chamado'
        verbose_name_plural = 'chamados'

    def __str__(self):
        return f'<Report {self.id}: {self.title}>'

    @property
    def urgency_votes_count(self):
        return self.urgency_votes.count()

    @property
    def status_display(self):
        status_map = {
            'aberto': 'Aberto',
            'visualizado': 'Visualizado',
            'em_andamento': 'Em Andamento',
            'em_execucao': 'Em Execução',
            'concluido': 'Concluído',
            'avaliado': 'Avaliado',
            'rejeitado': 'Rejeitado',
            'resolvido': 'Resolvido',
        }
        return status_map.get(self.status, status_map.get(self.api_status, self.api_status))

    @property
    def api_status(self):
        alias_map = {'em_andamento': 'em_execucao'}
        return alias_map.get(self.status, self.status)

    @property
    def status_color(self):
        color_map = {
            'aberto': 'danger',
            'visualizado': 'info',
            'em_andamento': 'warning',
            'em_execucao': 'warning',
            'concluido': 'success',
            'resolvido': 'success',
            'avaliado': 'primary',
            'rejeitado': 'secondary',
        }
        return color_map.get(self.status, 'secondary')

    def to_dict(self, include_image_url=True):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'lat': self.lat,
            'lng': self.lng,
            'status': self.api_status,
            'status_display': self.status_display,
            'status_color': self.status_color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'user_id': self.user_id,
            'assigned_to': self.assigned_user_id,
            'urgency_votes_count': self.urgency_votes_count,
        }
        if self.user:
            data['user_name'] = self.user.name
        if self.assigned_user:
            data['assigned_name'] = self.assigned_user.name
        if include_image_url and self.image_path:
            data['image_url'] = f'{settings.MEDIA_URL}{os.path.basename(self.image_path)}'
        elif self.image_path:
            data['image_path'] = self.image_path
        return data


class ReportHistory(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='history', db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='actions_made'
    )
    action = models.CharField(max_length=50)
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'report_history'
        verbose_name = 'histórico do chamado'
        verbose_name_plural = 'históricos dos chamados'

    def __str__(self):
        return f'<ReportHistory {self.id}: {self.action} on Report {self.report_id}>'

    def to_dict(self):
        data = {
            'id': self.id,
            'report_id': self.report_id,
            'user_id': self.user_id,
            'action': self.action,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if self.user:
            data['user_name'] = self.user.name
            data['user_type'] = self.user.user_type
        return data


class ReportUrgencyVote(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='urgency_votes', db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='urgency_votes', db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'report_urgency_vote'
        verbose_name = 'voto de urgência'
        verbose_name_plural = 'votos de urgência'
        constraints = [
            models.UniqueConstraint(
                fields=['report', 'user'],
                name='uq_report_urgency_vote_report_user'
            )
        ]

    def __str__(self):
        return f'<ReportUrgencyVote report={self.report_id} user={self.user_id}>'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', db_index=True
    )
    report = models.ForeignKey(
        Report, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='notifications', db_index=True
    )
    message = models.TextField()
    type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'notification'
        verbose_name = 'notificação'
        verbose_name_plural = 'notificações'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'report_id': self.report_id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
