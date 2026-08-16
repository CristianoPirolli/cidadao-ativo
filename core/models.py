"""
Modelos Django para o sistema Cidadão Ativo
Migrado de Flask-SQLAlchemy para Django ORM
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, name, password=None, email=None, **extra_fields):
        user = self.model(name=name, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('user_type', 'admin')
        return self.create_user(name=name, email=email, password=password, **extra_fields)


class User(AbstractBaseUser):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    user_type = models.CharField(max_length=20, default='cidadao', db_index=True)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True, db_index=True)
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, db_index=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    orgao_nome = models.CharField(max_length=200, null=True, blank=True)

    # Comprovante de residência (cidadãos)
    residence_proof_path = models.CharField(max_length=255, null=True, blank=True)
    residence_proof_type = models.CharField(max_length=50, null=True, blank=True)

    # Município do órgão
    municipio_ibge_id = models.IntegerField(null=True, blank=True, db_index=True)
    municipio_nome = models.CharField(max_length=100, null=True, blank=True)
    municipio_uf = models.CharField(max_length=2, null=True, blank=True)

    # Município de origem do cidadão
    municipio_origem_id = models.IntegerField(null=True, blank=True, db_index=True)
    municipio_origem_nome = models.CharField(max_length=100, null=True, blank=True)
    municipio_origem_uf = models.CharField(max_length=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False, db_index=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    approved_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approved_users'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    migration_status = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.email or self.name

    # Propriedades de tipo
    @property
    def is_citizen(self):
        return self.user_type == 'cidadao'

    @property
    def is_agency(self):
        return self.user_type == 'orgao'

    @property
    def is_platform_owner(self):
        owner_email = (settings.PLATFORM_OWNER_EMAIL or '').strip().lower()
        user_email = (self.email or '').strip().lower()
        return bool(owner_email and user_email and owner_email == user_email)

    # Necessário para o Django admin
    @property
    def is_staff(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'user_type': self.user_type,
            'telefone': self.telefone,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'is_approved': self.is_approved,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'migration_status': self.migration_status,
        }
        if self.approved_by:
            data['approved_by_name'] = self.approved_by.name
        if include_sensitive:
            data['cpf'] = self.cpf
            if self.user_type == 'cidadao':
                data['residence_proof_type'] = self.residence_proof_type
                data['municipio_origem_nome'] = self.municipio_origem_nome
                data['municipio_origem_uf'] = self.municipio_origem_uf
        return data


class Report(models.Model):
    title = models.CharField(max_length=140, db_index=True)
    description = models.TextField()
    category = models.CharField(max_length=50, db_index=True)
    lat = models.FloatField()
    lng = models.FloatField()
    image_path = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, default='aberto', db_index=True)
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
            data['user_email'] = self.user.email
        if self.assigned_user:
            data['assigned_name'] = self.assigned_user.name
        if include_image_url and self.image_path:
            import os
            data['image_url'] = f'/uploads/{os.path.basename(self.image_path)}'
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


class ApprovalRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='approval_requests', db_index=True
    )
    agency = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approvals_made', db_index=True
    )
    status = models.CharField(max_length=20, default='pending', db_index=True)
    rejection_reason = models.TextField(null=True, blank=True)
    requested_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'approval_request'

    def to_dict(self):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'agency_id': self.agency_id,
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if self.user:
            data['user_name'] = self.user.name
            data['user_cpf'] = self.user.cpf
            data['user_telefone'] = self.user.telefone
            data['municipio'] = self.user.municipio_origem_nome
            data['uf'] = self.user.municipio_origem_uf
        if self.agency:
            data['agency_name'] = self.agency.orgao_nome
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
        constraints = [
            models.UniqueConstraint(
                fields=['report', 'user'],
                name='uq_report_urgency_vote_report_user'
            )
        ]

    def __str__(self):
        return f'<ReportUrgencyVote report={self.report_id} user={self.user_id}>'


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

    def __str__(self):
        return f'<OuvidoriaMessage {self.id} municipio={self.municipio_ibge_id}>'
