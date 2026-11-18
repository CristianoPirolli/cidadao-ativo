"""Avisos por e-mail ao cidadão que abriu o chamado."""
from django.urls import reverse

from apps.core.services.email import send_templated_email
from apps.reports.models import ReportStatus


def notify_report_update(report, actor, request, *, new_status=None, comment=''):
    """
    Avisa o autor do chamado sobre mudança de status ou comentário do órgão.

    Não envia se o autor não tem e-mail ou se foi ele mesmo quem agiu.
    """
    author = report.user
    if not author or not author.email or author.pk == actor.pk:
        return

    status_label = ReportStatus(new_status).label if new_status else None
    if status_label:
        subject = f'Chamado #{report.id}: {status_label}'
    else:
        subject = f'Chamado #{report.id}: nova mensagem do órgão'

    send_templated_email(subject, [author.email], 'emails/report_update', {
        'name': author.name,
        'report': report,
        'status_label': status_label,
        'comment': comment,
        'agency_name': actor.orgao_nome or actor.name,
        'link': request.build_absolute_uri(reverse('report_detail', args=[report.id])),
    })
