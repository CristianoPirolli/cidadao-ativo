from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models import User, Report, ReportHistory, Notification, ApprovalRequest, ReportUrgencyVote, OuvidoriaMessage


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('name', 'email', 'user_type', 'is_approved', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_approved', 'is_active', 'is_admin')
    search_fields = ('name', 'email', 'cpf', 'cnpj')
    ordering = ('-created_at',)
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('name', 'email', 'password')}),
        ('Tipo', {'fields': ('user_type', 'cpf', 'cnpj', 'orgao_nome', 'telefone')}),
        ('Município', {'fields': ('municipio_ibge_id', 'municipio_nome', 'municipio_uf', 'municipio_origem_id', 'municipio_origem_nome', 'municipio_origem_uf')}),
        ('Status', {'fields': ('is_active', 'is_admin', 'is_approved', 'approved_by', 'approved_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'email', 'user_type', 'password1', 'password2'),
        }),
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'status', 'municipio_nome', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description', 'municipio_nome')
    ordering = ('-created_at',)


@admin.register(ReportHistory)
class ReportHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'report', 'user', 'action', 'created_at')
    list_filter = ('action',)
    ordering = ('-created_at',)


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'agency', 'status', 'requested_at')
    list_filter = ('status',)
    ordering = ('-requested_at',)


@admin.register(OuvidoriaMessage)
class OuvidoriaMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'municipio_nome', 'is_active', 'created_at')
    list_filter = ('is_active', 'municipio_uf')
    ordering = ('-created_at',)
