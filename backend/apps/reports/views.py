"""Páginas de chamados (abertura e detalhe)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.reports.models import Report, ReportHistory, ReportUrgencyVote


@login_required
def denuncia(request):
    return render(request, 'reports/report_form.html')


@login_required
def report_detail(request, report_id):
    report = get_object_or_404(Report.objects.select_related('user', 'assigned_user'), pk=report_id)
    user = request.user

    if user.is_citizen:
        same_city = (
            user.municipio_origem_id is not None
            and report.municipio_ibge_id == user.municipio_origem_id
        )
        if not same_city and report.user_id != user.id:
            messages.error(request, 'Você não tem permissão para visualizar este chamado')
            return redirect('dashboard')

    if user.is_agency and not report.viewed_at:
        report.viewed_at = timezone.now()
        report.save(update_fields=['viewed_at'])
        ReportHistory.objects.create(
            report=report,
            user=user,
            action='visualizado',
            old_status=report.status,
            new_status=report.status,
            comment='Chamado visualizado pelo órgão responsável',
        )

    history = ReportHistory.objects.filter(report=report).select_related('user').order_by('created_at')
    has_voted_urgency = (
        user.is_citizen and ReportUrgencyVote.objects.filter(report=report, user=user).exists()
    )

    return render(request, 'reports/report_detail.html', {
        'report': report,
        'history': history,
        'has_voted_urgency': has_voted_urgency,
    })
