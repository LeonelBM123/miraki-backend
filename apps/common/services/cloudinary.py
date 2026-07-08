import importlib
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class CloudinaryUploadError(Exception):
    pass


def _configure_cloudinary():
    cloudinary = importlib.import_module('cloudinary')
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_image(file, *, folder):
    _configure_cloudinary()
    uploader = importlib.import_module('cloudinary.uploader')
    result = uploader.upload(file, folder=folder, resource_type='image')
    secure_url = result.get('secure_url')
    public_id = result.get('public_id')
    if not secure_url or not public_id:
        raise CloudinaryUploadError('Cloudinary no devolvio secure_url/public_id.')
    return {
        'secure_url': secure_url,
        'public_id': public_id,
    }


def delete_image(public_id):
    if not public_id:
        return False

    try:
        _configure_cloudinary()
        uploader = importlib.import_module('cloudinary.uploader')
        result = uploader.destroy(public_id, resource_type='image')
    except Exception:
        logger.warning('No se pudo eliminar imagen en Cloudinary.', exc_info=True)
        return False

    status = result.get('result') if isinstance(result, dict) else None
    if status in {'ok', 'not found'}:
        return True

    logger.warning('Cloudinary devolvio resultado inesperado al eliminar imagen.')
    return False
