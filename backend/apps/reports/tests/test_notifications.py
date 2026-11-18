import json
from unittest import mock

import pytest
from django.urls import reverse

SEND = 'apps.reports.services.notifications.send_templated_email'


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type='application/json')


@pytest.mark.django_db
def test_status_change_emails_the_author(client, agency, report):
    client.force_login(agency)
    with mock.patch(SEND) as send:
        post_json(client, reverse('api_update_report', args=[report.id]), {'status': 'em_andamento', 'comment': 'Equipe a caminho'})
    subject, recipients, template, context = send.call_args.args
    assert recipients == ['maria@example.com']
    assert 'Em Andamento' in subject
    assert context['comment'] == 'Equipe a caminho'
    assert context['link'].endswith(reverse('report_detail', args=[report.id]))


@pytest.mark.django_db
def test_agency_comment_emails_the_author(client, agency, report):
    client.force_login(agency)
    with mock.patch(SEND) as send:
        post_json(client, reverse('api_add_comment', args=[report.id]), {'comment': 'Vistoria agendada'})
    assert send.call_args.args[1] == ['maria@example.com']


@pytest.mark.django_db
def test_no_email_when_status_does_not_change(client, agency, report):
    client.force_login(agency)
    with mock.patch(SEND) as send:
        post_json(client, reverse('api_update_report', args=[report.id]), {'status': report.status})
    send.assert_not_called()


@pytest.mark.django_db
def test_no_email_when_author_has_no_email(client, agency, report, citizen):
    citizen.email = None
    citizen.save()
    client.force_login(agency)
    with mock.patch(SEND) as send:
        post_json(client, reverse('api_update_report', args=[report.id]), {'status': 'resolvido'})
    send.assert_not_called()


def test_email_templates_escape_user_content(db, citizen, report):
    from django.template.loader import render_to_string
    report.title = '<script>alert(1)</script>'
    html = render_to_string('emails/report_update.html', {'name': citizen.name, 'report': report, 'status_label': 'Resolvido',
                                                          'comment': '<b>oi</b>', 'agency_name': 'Prefeitura', 'link': 'https://x/report/1'})
    assert '<script>' not in html and '&lt;script&gt;' in html
