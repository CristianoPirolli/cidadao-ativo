import os
from datetime import timedelta

import pytest
from django.conf import settings
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import ApprovalRequest


def make_proof(user):
    relative = f'residence_proofs/{user.id}/comprovante.pdf'
    path = os.path.join(settings.MEDIA_ROOT, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'%PDF-1.4')
    user.residence_proof_path = relative
    user.save()
    return path


@pytest.mark.django_db
def test_privacy_page_shows_configured_contact(client, settings):
    settings.PRIVACY_CONTACT_EMAIL = 'dpo@prefeitura.gov.br'
    settings.RESIDENCE_PROOF_RETENTION_DAYS = 60
    html = client.get(reverse('privacy_policy')).content.decode()
    assert 'dpo@prefeitura.gov.br' in html
    assert '60 dias' in html


@pytest.mark.django_db
def test_register_page_links_privacy_policy(client):
    html = client.get(reverse('register')).content.decode()
    assert 'name="accept_privacy"' in html
    assert reverse('privacy_policy') in html


@pytest.mark.django_db
def test_purge_removes_old_proofs_only(citizen, other_citizen, settings):
    settings.RESIDENCE_PROOF_RETENTION_DAYS = 90
    old_path = make_proof(citizen)
    citizen.approved_at = timezone.now() - timedelta(days=91)
    citizen.save()
    recent_path = make_proof(other_citizen)
    other_citizen.approved_at = timezone.now() - timedelta(days=10)
    other_citizen.save()

    call_command('purge_residence_proofs')

    citizen.refresh_from_db()
    other_citizen.refresh_from_db()
    assert not os.path.exists(old_path) and citizen.residence_proof_path is None
    assert os.path.exists(recent_path) and other_citizen.residence_proof_path


@pytest.mark.django_db
def test_purge_removes_proofs_of_old_rejections(citizen, agency, settings):
    path = make_proof(citizen)
    citizen.is_approved = False
    citizen.is_active = False
    citizen.save()
    ApprovalRequest.objects.create(user=citizen, agency=agency, status='rejected',
                                   resolved_at=timezone.now() - timedelta(days=settings.RESIDENCE_PROOF_RETENTION_DAYS + 1))
    call_command('purge_residence_proofs')
    assert not os.path.exists(path)


@pytest.mark.django_db
def test_purge_dry_run_keeps_files(citizen):
    path = make_proof(citizen)
    citizen.approved_at = timezone.now() - timedelta(days=365)
    citizen.save()
    call_command('purge_residence_proofs', '--dry-run')
    assert os.path.exists(path)


@pytest.mark.django_db
def test_vlibras_widget_follows_setting(client, settings):
    settings.VLIBRAS_ENABLED = True
    assert 'vlibras.gov.br' in client.get('/login').content.decode()
    settings.VLIBRAS_ENABLED = False
    assert 'vlibras.gov.br' not in client.get('/login').content.decode()
