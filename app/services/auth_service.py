"""
Serviços relacionados à autenticação e registro de usuários.
Centraliza regras de negócio que antes ficavam espalhadas nas rotas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from werkzeug.security import check_password_hash, generate_password_hash

from app.models.models import ApprovalRequest, User, db
from app.services.cnpj_validation import clean_cnpj, validate_cnpj
from app.services.cpf_validation import clean_cpf, validate_cpf
from app.services.document_validation import save_residence_proof


class AuthenticationError(Exception):
    """Erro levantado quando o login falha."""


class RegistrationError(Exception):
    """Erro levantado quando o cadastro falha."""

    def __init__(self, messages: Iterable[str]):
        messages_list = list(messages)
        super().__init__("\n".join(messages_list))
        self.messages = messages_list


@dataclass
class RegistrationResult:
    user: User
    message: str
    flash_category: str = "success"


CPF_PATTERN = re.compile(r"^\D*(\d\D*){11}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _normalise_identifier(raw_identifier: str) -> Tuple[str, str]:
    """
    Decide se o identificador informado é CPF ou email e devolve o campo e o valor tratado.
    """
    identifier = (raw_identifier or "").strip()
    if not identifier:
        raise AuthenticationError("Informe CPF ou email para entrar.")

    if EMAIL_PATTERN.match(identifier):
        return "email", identifier.lower()

    numbers_only = clean_cpf(identifier)
    if CPF_PATTERN.match(identifier) and len(numbers_only) == 11:
        return "cpf", numbers_only

    # Se não casar com nenhum formato conhecido, assume email para manter compatibilidade
    return "email", identifier.lower()


def authenticate_user(identifier: str, password: str) -> User:
    """
    Autentica um usuário por CPF ou email.
    """
    if not password:
        raise AuthenticationError("Informe a senha para continuar.")

    field, value = _normalise_identifier(identifier)
    user = User.query.filter_by(**{field: value}).first()

    if not user:
        raise AuthenticationError("Credenciais incorretas.")

    if not user.is_active:
        raise AuthenticationError("Esta conta está desativada. Entre em contato com o suporte.")

    if not user.is_admin and not user.is_approved:
        raise AuthenticationError("Sua conta ainda não foi aprovada pelo órgão responsável.")

    if not check_password_hash(user.password_hash, password):
        raise AuthenticationError("Credenciais incorretas.")

    user.last_login = datetime.utcnow()
    db.session.commit()
    return user


def _validate_common_fields(form: Mapping[str, str]) -> Tuple[Dict[str, str], List[str]]:
    """
    Valida campos comuns a qualquer tipo de usuário.
    Retorna (dados_formatados, lista_de_erros)
    """
    errors: List[str] = []

    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password") or ""
    telefone = (form.get("telefone") or "").strip()
    user_type = form.get("user_type", "cidadao") or "cidadao"

    if not name:
        errors.append("Nome é obrigatório.")

    if len(password) < 8:
        errors.append("Senha deve ter pelo menos 8 caracteres.")
    elif password != confirm_password:
        errors.append("As senhas não conferem.")

    if user_type not in {"cidadao", "orgao"}:
        errors.append("Tipo de usuário inválido.")

    if email:
        if not EMAIL_PATTERN.match(email):
            errors.append("Email inválido.")
        elif User.query.filter_by(email=email).first():
            errors.append("Este email já está cadastrado.")

    data = {
        "name": name,
        "email": email or None,
        "password": password,
        "telefone": telefone or None,
        "user_type": user_type,
    }

    return data, errors


def _validate_citizen_fields(form: Mapping[str, str]) -> Tuple[Dict[str, Optional[str]], List[str]]:
    """
    Valida campos específicos de cidadãos.
    """
    errors: List[str] = []
    cpf = form.get("cpf") or ""
    municipio_id = form.get("municipio_origem_id")
    municipio_nome = form.get("municipio_origem_nome")
    municipio_uf = form.get("municipio_origem_uf")
    residence_proof_type = form.get("residence_proof_type")

    cpf_validation = validate_cpf(cpf)
    if not cpf_validation.get("valid"):
        errors.append(f"CPF inválido: {cpf_validation.get('message')}")
    else:
        cpf_clean = cpf_validation.get("cpf_clean")
        if User.query.filter_by(cpf=cpf_clean).first():
            errors.append("Este CPF já está cadastrado.")
    cpf_clean = cpf_validation.get("cpf_clean") if cpf_validation.get("valid") else None

    if not municipio_id or not municipio_nome or not municipio_uf:
        errors.append("Município de origem é obrigatório para cidadãos.")

    if not residence_proof_type:
        errors.append("Tipo de comprovante de residência é obrigatório.")

    return (
        {
            "cpf": cpf_clean,
            "municipio_origem_id": municipio_id,
            "municipio_origem_nome": municipio_nome,
            "municipio_origem_uf": municipio_uf,
            "residence_proof_type": residence_proof_type,
        },
        errors,
    )


def _validate_agency_fields(form: Mapping[str, str]) -> Tuple[Dict[str, Optional[str]], List[str]]:
    """
    Valida campos específicos de órgãos públicos.
    """
    errors: List[str] = []
    cnpj = form.get("cnpj") or ""
    orgao_nome = (form.get("orgao_nome") or "").strip()
    municipio_id = form.get("municipio_ibge_id")
    municipio_nome = form.get("municipio_nome")
    municipio_uf = form.get("municipio_uf")

    if not cnpj or not orgao_nome:
        errors.append("CNPJ e nome do órgão são obrigatórios.")
    else:
        validation = validate_cnpj(cnpj, use_api=True)
        if not validation.get("valid"):
            errors.append(f"CNPJ inválido: {validation.get('message')}")
        else:
            cnpj_clean = clean_cnpj(cnpj)
            if User.query.filter_by(cnpj=cnpj_clean).first():
                errors.append("Este CNPJ já está cadastrado.")

    if not municipio_id or not municipio_nome or not municipio_uf:
        errors.append("Município do órgão é obrigatório.")

    return (
        {
            "cnpj": clean_cnpj(cnpj) if cnpj else None,
            "orgao_nome": orgao_nome or None,
            "municipio_ibge_id": municipio_id,
            "municipio_nome": municipio_nome,
            "municipio_uf": municipio_uf,
        },
        errors,
    )


def register_user(form: Mapping[str, str], files: Mapping[str, object]) -> RegistrationResult:
    """
    Registra um novo usuário a partir dos dados do formulário.
    """
    base_data, errors = _validate_common_fields(form)
    user_type = base_data["user_type"]

    extra_data: Dict[str, Optional[str]] = {
        "cpf": None,
        "cnpj": None,
        "orgao_nome": None,
        "municipio_ibge_id": None,
        "municipio_nome": None,
        "municipio_uf": None,
        "municipio_origem_id": None,
        "municipio_origem_nome": None,
        "municipio_origem_uf": None,
        "residence_proof_type": None,
    }

    if user_type == "cidadao":
        citizen_data, citizen_errors = _validate_citizen_fields(form)
        errors.extend(citizen_errors)
        extra_data.update(citizen_data)
    else:
        agency_data, agency_errors = _validate_agency_fields(form)
        errors.extend(agency_errors)
        extra_data.update(agency_data)

    if errors:
        raise RegistrationError(errors)

    # Preparar dados para criação
    password_hash = generate_password_hash(base_data["password"])
    is_approved = user_type == "orgao"

    user = User(
        name=base_data["name"],
        email=base_data["email"],
        password_hash=password_hash,
        user_type=user_type,
        telefone=base_data["telefone"],
        cpf=extra_data["cpf"],
        cnpj=extra_data["cnpj"],
        orgao_nome=extra_data["orgao_nome"],
        is_approved=is_approved,
        municipio_ibge_id=int(extra_data["municipio_ibge_id"]) if extra_data["municipio_ibge_id"] else None,
        municipio_nome=extra_data["municipio_nome"],
        municipio_uf=extra_data["municipio_uf"],
        municipio_origem_id=int(extra_data["municipio_origem_id"]) if extra_data["municipio_origem_id"] else None,
        municipio_origem_nome=extra_data["municipio_origem_nome"],
        municipio_origem_uf=extra_data["municipio_origem_uf"],
        residence_proof_type=extra_data["residence_proof_type"] if user_type == "cidadao" else None,
        is_active=True,
    )

    try:
        db.session.add(user)
        db.session.flush()

        if user_type == "cidadao":
            residence_proof = files.get("residence_proof")
            if not residence_proof or not getattr(residence_proof, "filename", ""):
                raise RegistrationError(["Comprovante de residência é obrigatório."])

            success, result_message, _ = save_residence_proof(
                residence_proof,
                user.id,
                extra_data["residence_proof_type"],
            )

            if not success:
                raise RegistrationError([f"Erro ao salvar comprovante: {result_message}"])

            user.residence_proof_path = result_message
            approval_request = ApprovalRequest(user_id=user.id, status="pending")
            db.session.add(approval_request)

            success_message = (
                "Cadastro realizado com sucesso! "
                "Sua conta está aguardando aprovação do órgão competente da sua cidade. "
                "Você receberá um email assim que for aprovada."
            )
        else:
            success_message = (
                "Cadastro de órgão realizado com sucesso! Você já pode fazer login."
            )

        db.session.commit()
        return RegistrationResult(user=user, message=success_message)

    except RegistrationError:
        db.session.rollback()
        raise
    except Exception as exc:
        db.session.rollback()
        raise RegistrationError([f"Erro interno ao registrar usuário: {exc}"]) from exc

