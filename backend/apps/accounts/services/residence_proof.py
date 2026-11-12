"""
Serviço de validação de documentos (comprovantes de residência)
"""
import os
import uuid

from django.conf import settings

from apps.core.services.files import validate_document_file

RESIDENCE_PROOF_EXTENSIONS = getattr(settings, 'RESIDENCE_PROOF_EXTENSIONS', {'pdf', 'jpg', 'jpeg', 'png'})
RESIDENCE_PROOF_MAX_SIZE = getattr(settings, 'RESIDENCE_PROOF_MAX_SIZE', 5 * 1024 * 1024)
RESIDENCE_PROOF_TYPES = getattr(settings, 'RESIDENCE_PROOF_TYPES', {})


def allowed_residence_proof(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in RESIDENCE_PROOF_EXTENSIONS


def validate_file_size(file):
    max_size = RESIDENCE_PROOF_MAX_SIZE
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f'Arquivo muito grande. Tamanho máximo: {max_mb:.1f}MB'
    if size == 0:
        return False, 'Arquivo vazio'
    return True, ''


def sanitize_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'pdf'
    ext = ''.join(ch for ch in ext if ch.isalnum()) or 'pdf'
    return f'{uuid.uuid4().hex}.{ext}'


def validate_residence_proof_type(proof_type):
    valid_types = RESIDENCE_PROOF_TYPES.keys()
    if not proof_type:
        return False, 'Tipo de comprovante é obrigatório'
    if proof_type not in valid_types:
        return False, f"Tipo de comprovante inválido. Tipos aceitos: {', '.join(valid_types)}"
    return True, ''


def save_residence_proof(file, user_id, proof_type):
    valid, error = validate_residence_proof_type(proof_type)
    if not valid:
        return False, error, None

    max_size_mb = RESIDENCE_PROOF_MAX_SIZE / (1024 * 1024)
    validation = validate_document_file(file, max_size_mb=int(max_size_mb))
    if not validation.get('valid'):
        return False, validation.get('message'), None

    filename = sanitize_filename(getattr(file, 'name', 'documento'))
    upload_dir = str(settings.MEDIA_ROOT)
    user_dir = os.path.join(upload_dir, 'residence_proofs', str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    filepath = os.path.join(user_dir, filename)
    try:
        with open(filepath, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        relative_path = os.path.join('residence_proofs', str(user_id), filename)
        return True, relative_path, filename
    except Exception as e:
        return False, f'Erro ao salvar arquivo: {e}', None


def delete_residence_proof(filepath):
    try:
        full_path = os.path.join(str(settings.MEDIA_ROOT), filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
            user_dir = os.path.dirname(full_path)
            if os.path.isdir(user_dir) and not os.listdir(user_dir):
                os.rmdir(user_dir)
            return True
        return False
    except Exception:
        return False


def get_residence_proof_path(filepath):
    return os.path.join(str(settings.MEDIA_ROOT), filepath) if filepath else None
