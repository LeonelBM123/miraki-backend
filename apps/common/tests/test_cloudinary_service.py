from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.common.services.cloudinary import CloudinaryUploadError, delete_image, upload_image


class CloudinaryServiceTests(SimpleTestCase):
    @patch('apps.common.services.cloudinary.importlib.import_module')
    def test_upload_image_returns_secure_url_and_public_id(self, import_module):
        cloudinary_module = SimpleNamespace(config=Mock())
        uploader_module = SimpleNamespace(upload=Mock(return_value={
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/example.jpg',
            'public_id': 'miraki/ninos/example',
        }))
        import_module.side_effect = [cloudinary_module, uploader_module]

        result = upload_image(Mock(), folder='miraki/ninos')

        self.assertEqual(result['secure_url'], 'https://res.cloudinary.com/demo/image/upload/example.jpg')
        self.assertEqual(result['public_id'], 'miraki/ninos/example')
        uploader_module.upload.assert_called_once()

    @patch('apps.common.services.cloudinary.importlib.import_module')
    def test_upload_image_requires_secure_url_and_public_id(self, import_module):
        cloudinary_module = SimpleNamespace(config=Mock())
        uploader_module = SimpleNamespace(upload=Mock(return_value={'secure_url': 'https://example.com/image.jpg'}))
        import_module.side_effect = [cloudinary_module, uploader_module]

        with self.assertRaises(CloudinaryUploadError):
            upload_image(Mock(), folder='miraki/ninos')

    @patch('apps.common.services.cloudinary.importlib.import_module')
    def test_delete_image_calls_destroy(self, import_module):
        cloudinary_module = SimpleNamespace(config=Mock())
        uploader_module = SimpleNamespace(destroy=Mock(return_value={'result': 'ok'}))
        import_module.side_effect = [cloudinary_module, uploader_module]

        result = delete_image('miraki/ninos/example')

        self.assertTrue(result)
        uploader_module.destroy.assert_called_once_with('miraki/ninos/example', resource_type='image')

    @patch('apps.common.services.cloudinary.importlib.import_module')
    def test_delete_image_with_null_public_id_does_not_call_cloudinary(self, import_module):
        result = delete_image(None)

        self.assertFalse(result)
        import_module.assert_not_called()

    @patch('apps.common.services.cloudinary.importlib.import_module')
    def test_delete_image_returns_false_on_controlled_error(self, import_module):
        cloudinary_module = SimpleNamespace(config=Mock())
        uploader_module = SimpleNamespace(destroy=Mock(side_effect=RuntimeError('boom')))
        import_module.side_effect = [cloudinary_module, uploader_module]

        result = delete_image('miraki/ninos/example')

        self.assertFalse(result)
