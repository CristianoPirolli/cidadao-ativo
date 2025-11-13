"""
Serviço de validação de documentos (comprovantes de residência)
"""
import os
import uuid
import re
from werkzeug.utils import secure_filename
from flask import current_app
from app.services.file_validation import validate_document_file


def allowed_residence_proof(filename):
    """
    Verifica se a extensão do arquivo é permitida para comprovante de residência

    Args:
        filename (str): Nome do arquivo

    Returns:
        bool: True se a extensão é permitida
    """
    if not filename or '.' not in filename:
        return False

    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('RESIDENCE_PROOF_EXTENSIONS', {'pdf', 'jpg', 'jpeg', 'png'})


def validate_file_size(file):
    """
    Valida o tamanho do arquivo

    Args:
        file: Objeto de arquivo do werkzeug

    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    max_size = current_app.config.get('RESIDENCE_PROOF_MAX_SIZE', 5 * 1024 * 1024)

    # Verificar tamanho do arquivo
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset para o início

    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"Arquivo muito grande. Tamanho máximo: {max_mb:.1f}MB"

    if size == 0:
        return False, "Arquivo vazio"

    return True, ""


def sanitize_filename(filename):
    """
    Sanitiza o nome do arquivo e gera um nome único

    Args:
        filename (str): Nome original do arquivo

    Returns:
        str: Nome sanitizado e único
    """
    # Pegar apenas a extensão
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
    else:
        ext = 'pdf'

    # Gerar nome único
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    return secure_filename(unique_name)


def validate_residence_proof_type(proof_type):
    """
    Valida se o tipo de comprovante é válido

    Args:
        proof_type (str): Tipo do comprovante

    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
    """
    valid_types = current_app.config.get('RESIDENCE_PROOF_TYPES', {}).keys()

    if not proof_type:
        return False, "Tipo de comprovante é obrigatório"

    if proof_type not in valid_types:
        return False, f"Tipo de comprovante inválido. Tipos aceitos: {', '.join(valid_types)}"

    return True, ""


def save_residence_proof(file, user_id, proof_type):
    """
    Salva o comprovante de residência de forma segura

    Args:
        file: Objeto de arquivo do werkzeug
        user_id (int): ID do usuário
        proof_type (str): Tipo do comprovante

    Returns:
        tuple: (bool, str, str) - (sucesso, caminho do arquivo ou mensagem de erro, nome do arquivo)
    """
    # Validar tipo de comprovante
    valid, error = validate_residence_proof_type(proof_type)
    if not valid:
        return False, error, None

    # Validar arquivo (robustamente - extensão, MIME type, tamanho)
    max_size_mb = current_app.config.get('RESIDENCE_PROOF_MAX_SIZE', 5 * 1024 * 1024) / (1024 * 1024)
    validation = validate_document_file(file, max_size_mb=int(max_size_mb))

    if not validation.get('valid'):
        return False, validation.get('message'), None

    # Gerar nome único
    filename = sanitize_filename(file.filename)

    # Criar diretório do usuário se não existir
    upload_dir = current_app.config.get('UPLOAD_FOLDER')
    user_dir = os.path.join(upload_dir, 'residence_proofs', str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    # Caminho completo do arquivo
    filepath = os.path.join(user_dir, filename)

    try:
        # Salvar arquivo
        file.save(filepath)

        # Retornar caminho relativo ao upload folder
        relative_path = os.path.join('residence_proofs', str(user_id), filename)

        return True, relative_path, filename

    except Exception as e:
        return False, f"Erro ao salvar arquivo: {str(e)}", None


def delete_residence_proof(filepath):
    """
    Remove um comprovante de residência

    Args:
        filepath (str): Caminho do arquivo a ser removido

    Returns:
        bool: True se removido com sucesso
    """
    try:
        upload_dir = current_app.config.get('UPLOAD_FOLDER')
        full_path = os.path.join(upload_dir, filepath)

        if os.path.exists(full_path):
            os.remove(full_path)

            # Tentar remover diretório do usuário se estiver vazio
            user_dir = os.path.dirname(full_path)
            if os.path.isdir(user_dir) and not os.listdir(user_dir):
                os.rmdir(user_dir)

            return True

        return False

    except Exception:
        return False


def get_residence_proof_path(filepath):
    """
    Retorna o caminho completo do comprovante

    Args:
        filepath (str): Caminho relativo do arquivo

    Returns:
        str: Caminho completo do arquivo
    """
    upload_dir = current_app.config.get('UPLOAD_FOLDER')
    return os.path.join(upload_dir, filepath) if filepath else None
