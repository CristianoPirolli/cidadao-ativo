"""
Modelos de dados do sistema Cidadão Ativo
"""
from datetime import datetime
from flask import url_for
from flask_login import UserMixin
import os

# Importação dinâmica para evitar circular imports
def get_db():
    from app import db
    return db

db = get_db()

class Report(db.Model):
    """Modelo para denúncias de problemas urbanos"""
    __tablename__ = "report"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="aberto", index=True)  # aberto, visualizado, em_andamento, concluido, avaliado, rejeitado
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    viewed_at = db.Column(db.DateTime, nullable=True)  # Quando foi visualizado pelo órgão

    # Conclusão pelo órgão
    completion_image = db.Column(db.String(255), nullable=True)  # Imagem da obra finalizada
    completed_at = db.Column(db.DateTime, nullable=True)  # Data de conclusão

    # Avaliação pelo cidadão
    rating = db.Column(db.Integer, nullable=True)  # Nota de 1 a 5
    citizen_feedback = db.Column(db.Text, nullable=True)  # Comentário do cidadão
    evaluation_image = db.Column(db.String(255), nullable=True)  # Foto do cidadão após obra
    evaluated_at = db.Column(db.DateTime, nullable=True)  # Data da avaliação

    # Município do chamado (onde foi aberto)
    municipio_ibge_id = db.Column(db.Integer, nullable=True, index=True)
    municipio_nome = db.Column(db.String(100), nullable=True)
    municipio_uf = db.Column(db.String(2), nullable=True)

    # Relacionamentos com usuários
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Cidadão que criou
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Órgão responsável

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='reports_created')
    assigned_user = db.relationship('User', foreign_keys=[assigned_to], backref='reports_assigned')

    def __repr__(self):
        return f'<Report {self.id}: {self.title}>'

    def to_dict(self, include_image_url=True):
        """Serializa o report para JSON"""
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "lat": self.lat,
            "lng": self.lng,
            "status": self.api_status,
            "status_display": self.status_display,
            "status_color": self.status_color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "viewed_at": self.viewed_at.isoformat() if self.viewed_at else None,
            "user_id": self.user_id,
            "assigned_to": self.assigned_to
        }

        # Incluir informações do usuário criador
        if self.user:
            data["user_name"] = self.user.name
            data["user_email"] = self.user.email

        # Incluir informações do órgão responsável
        if self.assigned_user:
            data["assigned_name"] = self.assigned_user.name

        if include_image_url and self.image_path:
            try:
                data["image_url"] = url_for(
                    "uploaded_file",
                    filename=os.path.basename(self.image_path),
                    _external=True
                )
            except RuntimeError:
                # Fora do contexto de request
                data["image_url"] = f"/uploads/{os.path.basename(self.image_path)}"
        elif self.image_path:
            data["image_path"] = self.image_path

        return data

    @property
    def status_display(self):
        """Retorna nome amigável do status"""
        status_map = {
            'aberto': 'Aberto',
            'visualizado': 'Visualizado',
            'em_andamento': 'Em Andamento',
            'em_execucao': 'Em Execução',
            'concluido': 'Concluído',
            'avaliado': 'Avaliado',
            'rejeitado': 'Rejeitado',
            'resolvido': 'Resolvido'
        }
        return status_map.get(self.status, status_map.get(self.api_status, self.api_status))

    @property
    def api_status(self):
        """Mapeia status internos para valores expostos na API"""
        alias_map = {
            'em_andamento': 'em_execucao'
        }
        return alias_map.get(self.status, self.status)

    @property
    def status_color(self):
        """Retorna cor do status para interface"""
        color_map = {
            'aberto': 'danger',
            'visualizado': 'info',
            'em_andamento': 'warning',
            'em_execucao': 'warning',
            'concluido': 'success',
            'resolvido': 'success',
            'avaliado': 'primary',
            'rejeitado': 'secondary'
        }
        return color_map.get(self.status, 'secondary')


class User(UserMixin, db.Model):
    """Modelo para usuários do sistema (cidadãos e órgãos)"""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)  # Opcional para cidadãos
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False, default='cidadao', index=True)  # 'cidadao', 'orgao' ou 'admin'
    cpf = db.Column(db.String(14), unique=True, nullable=True, index=True)
    cnpj = db.Column(db.String(18), unique=True, nullable=True, index=True)  # CNPJ - apenas para órgãos
    telefone = db.Column(db.String(20), nullable=True)
    orgao_nome = db.Column(db.String(200), nullable=True)  # Nome do órgão público

    # Comprovante de residência (apenas para user_type='cidadao')
    residence_proof_path = db.Column(db.String(255), nullable=True)  # Caminho do comprovante
    residence_proof_type = db.Column(db.String(50), nullable=True)  # Tipo: conta_luz, conta_agua, telefone, contrato, declaracao

    # Município do órgão (apenas para user_type='orgao')
    municipio_ibge_id = db.Column(db.Integer, nullable=True, index=True)
    municipio_nome = db.Column(db.String(100), nullable=True)
    municipio_uf = db.Column(db.String(2), nullable=True)

    # Município de origem do cidadão (apenas para user_type='cidadao')
    municipio_origem_id = db.Column(db.Integer, nullable=True, index=True)
    municipio_origem_nome = db.Column(db.String(100), nullable=True)
    municipio_origem_uf = db.Column(db.String(2), nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False, index=True)  # Administrador do sistema
    is_approved = db.Column(db.Boolean, default=False, index=True)  # Se foi aprovado por um órgão/admin
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Órgão/Admin que aprovou
    approved_at = db.Column(db.DateTime, nullable=True)  # Data de aprovação
    migration_status = db.Column(db.String(20), nullable=True)  # 'legacy' para usuários antigos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationship para quem aprovou
    approver = db.relationship('User', remote_side=[id], backref='approved_users', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self, include_sensitive=False):
        """Serializa o usuário para JSON"""
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "user_type": self.user_type,
            "telefone": self.telefone,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_approved": self.is_approved,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "migration_status": self.migration_status
        }

        if self.approver:
            data["approved_by_name"] = self.approver.name

        if include_sensitive:
            # Incluir dados mais sensíveis apenas quando necessário
            data["cpf"] = self.cpf
            if self.user_type == 'cidadao':
                data["residence_proof_type"] = self.residence_proof_type
                data["municipio_origem_nome"] = self.municipio_origem_nome
                data["municipio_origem_uf"] = self.municipio_origem_uf

        return data

    @property
    def is_citizen(self):
        """Verifica se o usuário é um cidadão"""
        return self.user_type == 'cidadao'

    @property
    def is_agency(self):
        """Verifica se o usuário é um órgão"""
        return self.user_type == 'orgao'

    # Métodos necessários para Flask-Login
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class ReportHistory(db.Model):
    """Modelo para histórico de alterações em denúncias"""
    __tablename__ = "report_history"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Quem fez a alteração
    action = db.Column(db.String(50), nullable=False)  # 'criado', 'visualizado', 'status_alterado', 'comentario'
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)
    comment = db.Column(db.Text, nullable=True)  # Comentários do órgão
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    report = db.relationship('Report', backref='history')
    user = db.relationship('User', backref='actions_made')

    def __repr__(self):
        return f'<ReportHistory {self.id}: {self.action} on Report {self.report_id}>'

    def to_dict(self):
        """Serializa o histórico para JSON"""
        data = {
            "id": self.id,
            "report_id": self.report_id,
            "user_id": self.user_id,
            "action": self.action,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        # Incluir informações do usuário que fez a ação
        if self.user:
            data["user_name"] = self.user.name
            data["user_type"] = self.user.user_type

        return data


class Notification(db.Model):
    """Modelo para notificações do sistema"""
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=True, index=True)  # Relacionado a um chamado
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'status_change', 'approval', 'evaluation', etc
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = db.relationship('User', backref='notifications')
    report = db.relationship('Report', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.id}: {self.type} for User {self.user_id}>'

    def to_dict(self):
        """Serializa a notificação para JSON"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "report_id": self.report_id,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ApprovalRequest(db.Model):
    """Modelo para histórico de solicitações de aprovação de cadastro"""
    __tablename__ = "approval_request"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)  # Cidadão solicitando aprovação
    agency_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # Órgão que analisou
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # 'pending', 'approved', 'rejected'
    rejection_reason = db.Column(db.Text, nullable=True)  # Motivo da rejeição
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # Data da solicitação
    resolved_at = db.Column(db.DateTime, nullable=True)  # Data da resolução

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='approval_requests')
    agency = db.relationship('User', foreign_keys=[agency_id], backref='approvals_made')

    def __repr__(self):
        return f'<ApprovalRequest {self.id}: User {self.user_id} - {self.status}>'

    def to_dict(self):
        """Serializa a solicitação para JSON"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "agency_id": self.agency_id,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }

        if self.user:
            data["user_name"] = self.user.name
            data["user_cpf"] = self.user.cpf
            data["user_telefone"] = self.user.telefone
            data["municipio"] = self.user.municipio_origem_nome
            data["uf"] = self.user.municipio_origem_uf

        if self.agency:
            data["agency_name"] = self.agency.orgao_nome

        return data
