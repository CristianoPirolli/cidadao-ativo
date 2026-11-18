"""Armazenamento e validação de comprovantes de residência."""
import os
import uuid

from django.conf import settings

from apps.core.services.files import validate_document_file


def sanitize_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'pdf'
    ext = ''.join(ch for ch in ext if ch.isalnum()) or 'pdf'
    return f'{uuid.uuid4().hex}.{ext}'


def validate_residence_proof_type(proof_type):
    valid_types = settings.RESIDENCE_PROOF_TYPES.keys()
    if not proof_type:
        return False, 'Tipo de comprovante é obrigatório'
    if proof_type not in valid_types:
        return False, f"Tipo de comprovante inválido. Tipos aceitos: {', '.join(valid_types)}"
    return True, ''


def save_residence_proof(file, user_id, proof_type):
    valid, error = validate_residence_proof_type(proof_type)
    if not valid:
        return False, error, None

    max_size_mb = settings.RESIDENCE_PROOF_MAX_SIZE // (1024 * 1024)
    validation = validate_document_file(file, max_size_mb=max_size_mb)
    if not validation.get('valid'):
        return False, validation.get('message'), None

    filename = sanitize_filename(getattr(file, 'name', 'documento'))
    relative_path = os.path.join('residence_proofs', str(user_id), filename)
    filepath = os.path.join(str(settings.MEDIA_ROOT), relative_path)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        with open(filepath, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
    except OSError as e:
        return False, f'Erro ao salvar arquivo: {e}', None
    return True, relative_path, filename
