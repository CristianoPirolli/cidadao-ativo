import pytest
from django.urls import reverse

from apps.accounts.models import ApprovalRequest, User
from conftest import MUNICIPIO


@pytest.mark.django_db
class TestLogin:
    def test_login_with_cpf(self, client, citizen):
        response = client.post(reverse('login'), {'login_id': '529.982.247-25', 'password': 'senha-forte-123'})
        assert response.status_code == 302
        assert response.url == reverse('dashboard')

    def test_login_with_email(self, client, citizen):
        response = client.post(reverse('login'), {'login_id': 'maria@example.com', 'password': 'senha-forte-123'})
        assert response.status_code == 302

    def test_wrong_password(self, client, citizen):
        response = client.post(reverse('login'), {'login_id': 'maria@example.com', 'password': 'errada'})
        assert response.status_code == 200
        assert '_auth_user_id' not in client.session

    def test_unapproved_user_cannot_login(self, client, citizen):
        citizen.is_approved = False
        citizen.save()
        client.post(reverse('login'), {'login_id': 'maria@example.com', 'password': 'senha-forte-123'})
        assert '_auth_user_id' not in client.session

    def test_open_redirect_is_blocked(self, client, citizen):
        response = client.post(
            reverse('login') + '?next=https://evil.example.com/',
            {'login_id': 'maria@example.com', 'password': 'senha-forte-123'},
        )
        assert response.url == reverse('dashboard')

    def test_safe_next_is_followed(self, client, citizen):
        response = client.post(
            reverse('login') + '?next=/ouvidoria',
            {'login_id': 'maria@example.com', 'password': 'senha-forte-123'},
        )
        assert response.url == '/ouvidoria'


@pytest.mark.django_db
def test_citizen_registration_creates_pending_request(client, png_file):
    response = client.post(reverse('register'), {
        'user_type': 'cidadao',
        'name': 'Novo Cidadão',
        'email': 'novo@example.com',
        'password': 'senha-forte-123',
        'confirm_password': 'senha-forte-123',
        'cpf': '529.982.247-25',
        'municipio_origem_id': MUNICIPIO['id'],
        'municipio_origem_nome': MUNICIPIO['nome'],
        'municipio_origem_uf': MUNICIPIO['uf'],
        'residence_proof_type': 'conta_luz',
        'residence_proof': png_file,
    })
    assert response.status_code == 302
    user = User.objects.get(email='novo@example.com')
    assert user.is_approved is False
    assert user.residence_proof_path.startswith('residence_proofs/')
    assert ApprovalRequest.objects.filter(user=user, status='pending').exists()


@pytest.mark.django_db
class TestApprovals:
    def test_approve_requires_post(self, client, admin_user, citizen):
        client.force_login(admin_user)
        response = client.get(reverse('approve_user', args=[citizen.id]))
        assert response.status_code == 405

    def test_admin_approves_user(self, client, admin_user, citizen):
        citizen.is_approved = False
        citizen.save()
        client.force_login(admin_user)
        client.post(reverse('approve_user', args=[citizen.id]))
        citizen.refresh_from_db()
        assert citizen.is_approved

    def test_citizen_cannot_approve(self, client, citizen, other_citizen):
        client.force_login(citizen)
        response = client.post(reverse('approve_user', args=[other_citizen.id]))
        assert response.status_code == 302
        assert response.url == reverse('dashboard')

    def test_agency_approves_citizen_from_same_city(self, client, agency, citizen):
        citizen.is_approved = False
        citizen.save()
        ApprovalRequest.objects.create(user=citizen)
        client.force_login(agency)
        client.post(reverse('agency_approve_citizen', args=[citizen.id]))
        citizen.refresh_from_db()
        assert citizen.is_approved
        assert ApprovalRequest.objects.get(user=citizen).status == 'approved'

    def test_owner_toggles_admin(self, client, owner, citizen):
        client.force_login(owner)
        client.post(reverse('toggle_admin', args=[citizen.id]))
        citizen.refresh_from_db()
        assert citizen.is_admin


@pytest.mark.django_db
def test_agency_from_other_city_cannot_see_residence_proof(client, agency, citizen):
    citizen.municipio_origem_id = 1
    citizen.residence_proof_path = 'residence_proofs/1/x.png'
    citizen.save()
    client.force_login(agency)
    response = client.get(reverse('view_residence_proof', args=[citizen.id]))
    assert response.status_code == 302


@pytest.mark.django_db
def test_registration_rejects_weak_password(client, png_file):
    client.post(reverse('register'), {
        'user_type': 'cidadao', 'name': 'Fraco', 'email': 'fraco@example.com',
        'password': '12345678', 'confirm_password': '12345678', 'cpf': '529.982.247-25',
        'municipio_origem_id': MUNICIPIO['id'], 'municipio_origem_nome': MUNICIPIO['nome'],
        'municipio_origem_uf': MUNICIPIO['uf'], 'residence_proof_type': 'conta_luz', 'residence_proof': png_file,
    })
    assert not User.objects.filter(email='fraco@example.com').exists()
