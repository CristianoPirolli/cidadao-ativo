"""Modelos de usuários e aprovação de cadastro."""
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserType(models.TextChoices):
    CITIZEN = 'cidadao', 'Cidadão'
    AGENCY = 'orgao', 'Órgão'
    ADMIN = 'admin', 'Administrador'


class UserManager(BaseUserManager):
    def create_user(self, name, password=None, email=None, **extra_fields):
        user = self.model(name=name, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('user_type', UserType.ADMIN)
        return self.create_user(name=name, email=email, password=password, **extra_fields)


class User(AbstractBaseUser):
    name = models.CharField('nome', max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    user_type = models.CharField(
        'tipo', max_length=20, choices=UserType.choices, default=UserType.CITIZEN, db_index=True
    )
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
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.email or self.name

    # Propriedades de tipo
    @property
    def is_citizen(self):
        return self.user_type == UserType.CITIZEN

    @property
    def is_agency(self):
        return self.user_type == UserType.AGENCY

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
            if self.is_citizen:
                data['residence_proof_type'] = self.residence_proof_type
                data['municipio_origem_nome'] = self.municipio_origem_nome
                data['municipio_origem_uf'] = self.municipio_origem_uf
        return data


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
        verbose_name = 'solicitação de aprovação'
        verbose_name_plural = 'solicitações de aprovação'

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
