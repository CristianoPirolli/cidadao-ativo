"""
Testes para a API REST
"""
import json
import pytest
from app.models.models import Report


class TestReportsAPI:
    """Testes para endpoints de reports"""

    def test_get_reports_empty(self, client):
        """Testa listagem de reports vazia"""
        response = client.get('/api/reports')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 0
        assert data['pagination']['total'] == 0

    def test_get_reports_with_data(self, client, sample_report):
        """Testa listagem com reports existentes"""
        response = client.get('/api/reports')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['title'] == 'Buraco na rua'

    def test_create_report_success(self, client):
        """Testa criação de report com sucesso"""
        response = client.post('/api/reports', data={
            'title': 'Lâmpada queimada',
            'description': 'Poste sem iluminação',
            'category': 'Iluminação',
            'lat': -23.55,
            'lng': -46.63
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['title'] == 'Lâmpada queimada'
        assert data['data']['status'] == 'aberto'

    def test_create_report_missing_fields(self, client):
        """Testa criação sem campos obrigatórios"""
        response = client.post('/api/reports', data={
            'title': 'Teste'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'errors' in data

    def test_create_report_invalid_coordinates(self, client):
        """Testa criação com coordenadas inválidas"""
        response = client.post('/api/reports', data={
            'title': 'Teste',
            'description': 'Desc',
            'category': 'Vias',
            'lat': 999,  # Inválido
            'lng': -46.63
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_get_report_by_id(self, client, sample_report):
        """Testa busca de report por ID"""
        response = client.get(f'/api/reports/{sample_report.id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == sample_report.id

    def test_get_report_not_found(self, client):
        """Testa busca de report inexistente"""
        response = client.get('/api/reports/999')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['success'] is False

    def test_update_report_status_authenticated(self, auth_client, sample_report):
        """Testa atualização de status (admin autenticado)"""
        response = auth_client.patch(
            f'/api/reports/{sample_report.id}',
            data=json.dumps({'status': 'em_execucao'}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['status'] == 'em_execucao'

    def test_update_report_status_unauthenticated(self, client, sample_report):
        """Testa atualização sem autenticação (deve falhar)"""
        response = client.patch(
            f'/api/reports/{sample_report.id}',
            data=json.dumps({'status': 'em_execucao'}),
            content_type='application/json'
        )

        # Flask-Login redireciona para login
        assert response.status_code == 401 or response.status_code == 302

    def test_delete_report_authenticated(self, auth_client, sample_report):
        """Testa deleção de report (admin autenticado)"""
        response = auth_client.delete(f'/api/reports/{sample_report.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_get_stats(self, client, sample_report):
        """Testa endpoint de estatísticas"""
        response = client.get('/api/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total'] == 1
        assert data['data']['by_status']['aberto'] == 1

    def test_pagination(self, client, app):
        """Testa paginação de reports"""
        with app.app_context():
            # Criar 15 reports
            for i in range(15):
                report = Report(
                    title=f'Report {i}',
                    description=f'Descrição {i}',
                    category='Vias',
                    lat=-23.55,
                    lng=-46.63
                )
                from app import db
                db.session.add(report)
            db.session.commit()

        # Pegar primeira página (10 itens)
        response = client.get('/api/reports?per_page=10&page=1')
        data = json.loads(response.data)

        assert len(data['data']) == 10
        assert data['pagination']['total'] == 15
        assert data['pagination']['pages'] == 2
        assert data['pagination']['has_next'] is True

        # Pegar segunda página (5 itens)
        response = client.get('/api/reports?per_page=10&page=2')
        data = json.loads(response.data)

        assert len(data['data']) == 5
        assert data['pagination']['has_next'] is False

    def test_filter_by_status(self, client, app):
        """Testa filtro por status"""
        with app.app_context():
            report1 = Report(
                title='Aberto', description='Desc', category='Vias',
                lat=-23.55, lng=-46.63, status='aberto'
            )
            report2 = Report(
                title='Resolvido', description='Desc', category='Vias',
                lat=-23.55, lng=-46.63, status='resolvido'
            )
            from app import db
            db.session.add_all([report1, report2])
            db.session.commit()

        response = client.get('/api/reports?status=aberto')
        data = json.loads(response.data)

        assert len(data['data']) == 1
        assert data['data'][0]['status'] == 'aberto'
