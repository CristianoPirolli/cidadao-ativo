import re
from unittest import mock

import pytest
from django.urls import reverse


def request_reset(client, identifier):
    with mock.patch('apps.accounts.forms.send_email') as send:
        response = client.post(reverse('password_reset'), {'email': identifier})
    return response, send


@pytest.mark.django_db
@pytest.mark.parametrize('identifier', ['529.982.247-25', 'MARIA@example.com'])
def test_reset_link_sent_by_cpf_or_email(client, citizen, identifier):
    response, send = request_reset(client, identifier)
    assert response.status_code == 302
    assert response.url == reverse('password_reset_done')
    send.assert_called_once()
    subject, recipients, html_body, text_body = send.call_args.args
    assert recipients == ['maria@example.com']
    assert '/senha/redefinir/' in text_body


@pytest.mark.django_db
def test_unknown_account_gets_same_response_without_email(client):
    response, send = request_reset(client, '111.444.777-35')
    assert response.url == reverse('password_reset_done')
    send.assert_not_called()


@pytest.mark.django_db
def test_citizen_without_email_gets_no_link(client, citizen):
    citizen.email = None
    citizen.save()
    response, send = request_reset(client, '529.982.247-25')
    assert response.url == reverse('password_reset_done')
    send.assert_not_called()


@pytest.mark.django_db
def test_full_reset_flow_changes_password(client, citizen):
    _, send = request_reset(client, 'maria@example.com')
    link = re.search(r'/senha/redefinir/\S+', send.call_args.args[3]).group(0)
    # O Django troca o token da URL por um valor de sessão e redireciona
    response = client.get(link, follow=True)
    form_url = response.redirect_chain[-1][0]
    response = client.post(form_url, {'new_password1': 'nova-senha-segura-9', 'new_password2': 'nova-senha-segura-9'})
    assert response.url == reverse('password_reset_complete')
    citizen.refresh_from_db()
    assert citizen.check_password('nova-senha-segura-9')
    # O link não pode ser reutilizado
    assert client.get(link, follow=True).context['validlink'] is False


@pytest.mark.django_db
def test_login_page_links_to_password_reset(client):
    assert reverse('password_reset') in client.get(reverse('login')).content.decode()
