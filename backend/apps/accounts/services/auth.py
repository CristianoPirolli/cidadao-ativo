"""
Serviços relacionados à autenticação e registro de usuários.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ApprovalRequest, User
from apps.accounts.services.residence_proof import save_residence_proof
from apps.core.services.cnpj import clean_cnpj, validate_cnpj
from apps.core.services.cpf import clean_cpf, validate_cpf


class AuthenticationError(Exception):
    """Erro levantado quando o login falha."""


class RegistrationError(Exception):
    """Erro levantado quando o cadastro falha."""

    def __init__(self, messages: Iterable[str]):
        messages_list = list(messages)
        super().__init__('\n'.join(messages_list))
        self.messages = messages_list


@dataclass
class RegistrationResult:
    user: User
    message: str
    flash_category: str = 'success'


CPF_PATTERN = re.compile(r'^\D*(\d\D*){11}$')
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def _normalise_identifier(raw_identifier: str) -> tuple[str, str]:
    identifier = (raw_identifier or '').strip()
    if not identifier:
        raise AuthenticationError('Informe CPF ou email para entrar.')

    if EMAIL_PATTERN.match(identifier):
        return 'email', identifier.lower()

    numbers_only = clean_cpf(identifier)
    if CPF_PATTERN.match(identifier) and len(numbers_only) == 11:
        return 'cpf', numbers_only

    return 'email', identifier.lower()


def authenticate_user(identifier: str, password: str) -> User:
    """Autentica um usuário por CPF ou email."""
    if not password:
        raise AuthenticationError('Informe a senha para continuar.')

    field, value = _normalise_identifier(identifier)
    user = User.objects.filter(**{field: value}).first()

    if not user:
        raise AuthenticationError('Credenciais incorretas.')

    if not user.is_active:
        raise AuthenticationError('Esta conta está desativada. Entre em contato com o suporte.')

    if not user.is_admin and not user.is_approved:
        raise AuthenticationError('Sua conta ainda não foi aprovada pelo órgão responsável.')

    if not user.check_password(password):
        raise AuthenticationError('Credenciais incorretas.')

    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    return user


def _validate_common_fields(form: Mapping[str, str]) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []

    name = (form.get('name') or '').strip()
    email = (form.get('email') or '').strip().lower()
    password = form.get('password') or ''
    confirm_password = form.get('confirm_password') or ''
    telefone = (form.get('telefone') or '').strip()
    user_type = form.get('user_type', 'cidadao') or 'cidadao'

    if not name:
        errors.append('Nome é obrigatório.')

    if password != confirm_password:
        errors.append('As senhas não conferem.')
    else:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors.extend(exc.messages)

    if user_type not in {'cidadao', 'orgao'}:
        errors.append('Tipo de usuário inválido.')

    if email:
        if not EMAIL_PATTERN.match(email):
            errors.append('Email inválido.')
        elif User.objects.filter(email=email).exists():
            errors.append('Este email já está cadastrado.')

    return {
        'name': name,
        'email': email or None,
        'password': password,
        'telefone': telefone or None,
        'user_type': user_type,
    }, errors


def _validate_citizen_fields(form: Mapping[str, str]) -> tuple[dict[str, str | None], list[str]]:
    errors: list[str] = []
    cpf = form.get('cpf') or ''
    municipio_id = form.get('municipio_origem_id')
    municipio_nome = form.get('municipio_origem_nome')
    municipio_uf = form.get('municipio_origem_uf')
    residence_proof_type = form.get('residence_proof_type')

    cpf_validation = validate_cpf(cpf)
    if not cpf_validation.get('valid'):
        errors.append(f"CPF inválido: {cpf_validation.get('message')}")
    else:
        cpf_clean = cpf_validation.get('cpf_clean')
        if User.objects.filter(cpf=cpf_clean).exists():
            errors.append('Este CPF já está cadastrado.')
    cpf_clean = cpf_validation.get('cpf_clean') if cpf_validation.get('valid') else None

    if not municipio_id or not municipio_nome or not municipio_uf:
        errors.append('Município de origem é obrigatório para cidadãos.')

    if not residence_proof_type:
        errors.append('Tipo de comprovante de residência é obrigatório.')

    return {
        'cpf': cpf_clean,
        'municipio_origem_id': municipio_id,
        'municipio_origem_nome': municipio_nome,
        'municipio_origem_uf': municipio_uf,
        'residence_proof_type': residence_proof_type,
    }, errors


def _validate_agency_fields(form: Mapping[str, str]) -> tuple[dict[str, str | None], list[str]]:
    errors: list[str] = []
    cnpj = form.get('cnpj') or ''
    orgao_nome = (form.get('orgao_nome') or '').strip()
    municipio_id = form.get('municipio_ibge_id')
    municipio_nome = form.get('municipio_nome')
    municipio_uf = form.get('municipio_uf')

    if not cnpj or not orgao_nome:
        errors.append('CNPJ e nome do órgão são obrigatórios.')
    else:
        validation = validate_cnpj(cnpj, use_api=True)
        if not validation.get('valid'):
            errors.append(f"CNPJ inválido: {validation.get('message')}")
        else:
            cnpj_clean = clean_cnpj(cnpj)
            if User.objects.filter(cnpj=cnpj_clean).exists():
                errors.append('Este CNPJ já está cadastrado.')

    if not municipio_id or not municipio_nome or not municipio_uf:
        errors.append('Município do órgão é obrigatório.')

    return {
        'cnpj': clean_cnpj(cnpj) if cnpj else None,
        'orgao_nome': orgao_nome or None,
        'municipio_ibge_id': municipio_id,
        'municipio_nome': municipio_nome,
        'municipio_uf': municipio_uf,
    }, errors


@transaction.atomic
def register_user(form: Mapping[str, str], files: Mapping[str, object]) -> RegistrationResult:
    """Registra um novo usuário a partir dos dados do formulário."""
    base_data, errors = _validate_common_fields(form)
    user_type = base_data['user_type']

    extra_data: dict[str, str | None] = {
        'cpf': None, 'cnpj': None, 'orgao_nome': None,
        'municipio_ibge_id': None, 'municipio_nome': None, 'municipio_uf': None,
        'municipio_origem_id': None, 'municipio_origem_nome': None, 'municipio_origem_uf': None,
        'residence_proof_type': None,
    }

    if user_type == 'cidadao':
        citizen_data, citizen_errors = _validate_citizen_fields(form)
        errors.extend(citizen_errors)
        extra_data.update(citizen_data)
    else:
        agency_data, agency_errors = _validate_agency_fields(form)
        errors.extend(agency_errors)
        extra_data.update(agency_data)

    if errors:
        raise RegistrationError(errors)

    user = User(
        name=base_data['name'],
        email=base_data['email'],
        user_type=user_type,
        telefone=base_data['telefone'],
        cpf=extra_data['cpf'],
        cnpj=extra_data['cnpj'],
        orgao_nome=extra_data['orgao_nome'],
        is_approved=False,
        municipio_ibge_id=int(extra_data['municipio_ibge_id']) if extra_data.get('municipio_ibge_id') else None,
        municipio_nome=extra_data['municipio_nome'],
        municipio_uf=extra_data['municipio_uf'],
        municipio_origem_id=int(extra_data['municipio_origem_id']) if extra_data.get('municipio_origem_id') else None,
        municipio_origem_nome=extra_data['municipio_origem_nome'],
        municipio_origem_uf=extra_data['municipio_origem_uf'],
        residence_proof_type=extra_data['residence_proof_type'] if user_type == 'cidadao' else None,
        is_active=True,
    )
    user.set_password(base_data['password'])

    try:
        user.save()

        if user_type == 'cidadao':
            residence_proof = files.get('residence_proof')
            if not residence_proof or not getattr(residence_proof, 'name', ''):
                raise RegistrationError(['Comprovante de residência é obrigatório.'])

            success, result_message, _ = save_residence_proof(
                residence_proof, user.id, extra_data['residence_proof_type']
            )
            if not success:
                raise RegistrationError([f'Erro ao salvar comprovante: {result_message}'])

            user.residence_proof_path = result_message
            user.save(update_fields=['residence_proof_path'])

            ApprovalRequest.objects.create(user=user, status='pending')

            success_message = (
                'Cadastro realizado com sucesso! '
                'Sua conta está aguardando aprovação do órgão competente da sua cidade. '
                'Você receberá um email assim que for aprovada.'
            )
        else:
            success_message = (
                'Cadastro de órgão realizado com sucesso! '
                'A conta da prefeitura está aguardando aprovação do administrador SaaS.'
            )

        return RegistrationResult(user=user, message=success_message)

    except RegistrationError:
        raise
    except Exception as exc:
        raise RegistrationError([f'Erro interno ao registrar usuário: {exc}']) from exc
