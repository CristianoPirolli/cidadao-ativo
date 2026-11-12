from django.contrib import admin

from apps.reports.models import Notification, Report, ReportHistory, ReportUrgencyVote


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


@admin.register(ReportUrgencyVote)
class ReportUrgencyVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'report', 'user', 'created_at')
    ordering = ('-created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    ordering = ('-created_at',)
