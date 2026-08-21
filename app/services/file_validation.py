"""
Serviço de validação de arquivos
"""
import os
from PIL import Image
from werkzeug.utils import secure_filename


# Extensões permitidas para imagens de reports
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Extensões permitidas para comprovantes de residência
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# MIME types permitidos para imagens
ALLOWED_IMAGE_MIME_TYPES = {
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp'
}

# MIME types permitidos para documentos
ALLOWED_DOCUMENT_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png'
}


def _get_filename(file) -> str:
    """Retorna o nome do arquivo compatível com Flask (filename) e Django (name)."""
    return getattr(file, 'filename', None) or getattr(file, 'name', '') or ''


def get_file_extension(filename: str) -> str:
    """
    Retorna a extensão do arquivo em minúsculas

    Args:
        filename: Nome do arquivo

    Returns:
        Extensão do arquivo sem o ponto
    """
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def allowed_image_file(filename: str) -> bool:
    """
    Verifica se a extensão do arquivo é permitida para imagens

    Args:
        filename: Nome do arquivo

    Returns:
        True se permitido, False caso contrário
    """
    return '.' in filename and get_file_extension(filename) in ALLOWED_IMAGE_EXTENSIONS


def allowed_document_file(filename: str) -> bool:
    """
    Verifica se a extensão do arquivo é permitida para documentos

    Args:
        filename: Nome do arquivo

    Returns:
        True se permitido, False caso contrário
    """
    return '.' in filename and get_file_extension(filename) in ALLOWED_DOCUMENT_EXTENSIONS


def validate_image_file(file, max_size_mb: int = 10) -> dict:
    """
    Valida um arquivo de imagem

    Args:
        file: Objeto FileStorage do Flask
        max_size_mb: Tamanho máximo em MB

    Returns:
        Dict com 'valid' (bool), 'message' (str), 'safe_filename' (str)
    """
    filename = _get_filename(file)
    if not file or not filename:
        return {
            'valid': False,
            'message': 'Nenhum arquivo fornecido'
        }

    # Validar extensão
    if not allowed_image_file(filename):
        return {
            'valid': False,
            'message': f'Tipo de arquivo não permitido. Use: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        }

    # Validar MIME type
    if file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return {
            'valid': False,
            'message': 'Tipo MIME do arquivo não permitido'
        }

    # Validar tamanho
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Resetar posição

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return {
            'valid': False,
            'message': f'Arquivo muito grande. Tamanho máximo: {max_size_mb}MB'
        }

    if file_size == 0:
        return {
            'valid': False,
            'message': 'Arquivo vazio'
        }

    # Verificar se realmente é uma imagem (tentando abrir com Pillow)
    try:
        file.seek(0)
        img = Image.open(file)
        img.verify()  # Verifica se é uma imagem válida
        file.seek(0)

        # Verificar formato da imagem
        file.seek(0)
        img = Image.open(file)
        if img.format.lower() not in ['png', 'jpeg', 'gif', 'webp']:
            return {
                'valid': False,
                'message': f'Formato de imagem não suportado: {img.format}'
            }
        file.seek(0)
    except Exception as e:
        return {
            'valid': False,
            'message': f'Arquivo não é uma imagem válida: {str(e)}'
        }

    # Gerar nome seguro
    safe_name = secure_filename(filename)

    return {
        'valid': True,
        'message': 'Arquivo válido',
        'safe_filename': safe_name,
        'file_size': file_size
    }


def validate_document_file(file, max_size_mb: int = 5) -> dict:
    """
    Valida um arquivo de documento (PDF ou imagem)

    Args:
        file: Objeto FileStorage do Flask
        max_size_mb: Tamanho máximo em MB

    Returns:
        Dict com 'valid' (bool), 'message' (str), 'safe_filename' (str)
    """
    filename = _get_filename(file)
    if not file or not filename:
        return {
            'valid': False,
            'message': 'Nenhum arquivo fornecido'
        }

    # Validar extensão
    if not allowed_document_file(filename):
        return {
            'valid': False,
            'message': f'Tipo de arquivo não permitido. Use: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
        }

    # Validar MIME type
    if file.content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        return {
            'valid': False,
            'message': 'Tipo MIME do arquivo não permitido'
        }

    # Validar tamanho
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Resetar posição

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return {
            'valid': False,
            'message': f'Arquivo muito grande. Tamanho máximo: {max_size_mb}MB'
        }

    if file_size == 0:
        return {
            'valid': False,
            'message': 'Arquivo vazio'
        }

    # Se for imagem, validar
    extension = get_file_extension(filename)
    if extension in ['jpg', 'jpeg', 'png']:
        try:
            file.seek(0)
            img = Image.open(file)
            img.verify()  # Verifica se é uma imagem válida
            file.seek(0)

            # Verificar formato
            img = Image.open(file)
            if img.format.lower() not in ['jpeg', 'png']:
                return {
                    'valid': False,
                    'message': f'Formato de imagem não suportado: {img.format}'
                }
            file.seek(0)
        except Exception as e:
            return {
                'valid': False,
                'message': f'Arquivo não é uma imagem válida: {str(e)}'
            }

    # Gerar nome seguro
    safe_name = secure_filename(filename)

    return {
        'valid': True,
        'message': 'Arquivo válido',
        'safe_filename': safe_name,
        'file_size': file_size
    }
