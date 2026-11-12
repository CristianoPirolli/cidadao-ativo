import pytest
from django.urls import reverse

from apps.ouvidoria.models import OuvidoriaMessage
from apps.ouvidoria.services.messages import OuvidoriaValidationError, validate_ouvidoria_message


def test_message_too_short():
    with pytest.raises(OuvidoriaValidationError):
        validate_ouvidoria_message('curta')


@pytest.mark.django_db
def test_citizen_posts_message(client, citizen):
    client.force_login(citizen)
    client.post(reverse('ouvidoria'), {'content': 'A praça do bairro precisa de mais iluminação.'})
    msg = OuvidoriaMessage.objects.get()
    assert msg.municipio_ibge_id == citizen.municipio_origem_id


@pytest.mark.django_db
def test_list_only_shows_own_city(client, citizen, other_citizen):
    OuvidoriaMessage.objects.create(
        user=other_citizen, municipio_ibge_id=1, municipio_nome='Outra', municipio_uf='SP',
        content='Mensagem de outra cidade qualquer',
    )
    client.force_login(citizen)
    response = client.get(reverse('ouvidoria'))
    assert response.status_code == 200
    assert len(response.context['messages_list']) == 0


@pytest.mark.django_db
def test_only_owner_can_deactivate(client, citizen, owner):
    msg = OuvidoriaMessage.objects.create(
        user=citizen, municipio_ibge_id=1, municipio_nome='X', municipio_uf='SC', content='Mensagem de teste longa',
    )
    client.force_login(citizen)
    client.post(reverse('inativar_mensagem_ouvidoria', args=[msg.id]))
    msg.refresh_from_db()
    assert msg.is_active

    client.force_login(owner)
    client.post(reverse('inativar_mensagem_ouvidoria', args=[msg.id]))
    msg.refresh_from_db()
    assert not msg.is_active
