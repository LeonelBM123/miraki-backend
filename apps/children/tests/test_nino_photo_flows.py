from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Rol, Tutor
from apps.audit.models import Bitacora
from apps.children.models import Nino
from apps.institutions.models import AdminCentro

Usuario = get_user_model()


def image_file(name='photo.jpg', image_format='JPEG', content_type='image/jpeg', size=(8, 8)):
    buffer = BytesIO()
    Image.new('RGB', size, color='blue').save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class NinoPhotoFlowTests(APITestCase):
    def setUp(self):
        rol_tutor = Rol.objects.get(nombre_rol='Tutor')
        rol_admin = Rol.objects.get(nombre_rol='AdminCentro')
        self.user_a = Usuario.objects.create_user('photo-a@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.user_b = Usuario.objects.create_user('photo-b@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.admin_user = Usuario.objects.create_user('photo-admin@example.com', 'StrongPass123!', id_rol=rol_admin)
        self.tutor_a = Tutor.objects.create(id_usuario=self.user_a, nombre='Tutor A', telefono='70000101')
        self.tutor_b = Tutor.objects.create(id_usuario=self.user_b, nombre='Tutor B', telefono='70000102')

    def test_create_nino_without_photo_still_works(self):
        self.client.force_authenticate(self.user_a)

        response = self.client.post('/api/v1/children/ninos/', {'nombre': 'Sin Foto'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        nino = Nino.objects.get(nombre='Sin Foto')
        self.assertIsNone(nino.foto_url)
        self.assertIsNone(nino.foto_public_id)

    def test_create_nino_with_valid_jpg_photo(self):
        self.client.force_authenticate(self.user_a)

        with patch('apps.children.services.upload_image', return_value={
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/new.jpg',
            'public_id': 'miraki/ninos/new',
        }) as upload:
            response = self.client.post('/api/v1/children/ninos/', {
                'nombre': 'Con Foto',
                'foto': image_file(),
            }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        upload.assert_called_once()
        nino = Nino.objects.get(nombre='Con Foto')
        self.assertEqual(nino.foto_url, 'https://res.cloudinary.com/demo/image/upload/new.jpg')
        self.assertEqual(nino.foto_public_id, 'miraki/ninos/new')
        self.assertEqual(response.data['foto_url'], nino.foto_url)

    def test_create_nino_accepts_png_and_webp(self):
        self.client.force_authenticate(self.user_a)

        with patch('apps.children.services.upload_image', side_effect=[
            {'secure_url': 'https://res.cloudinary.com/demo/image/upload/png.png', 'public_id': 'miraki/ninos/png'},
            {'secure_url': 'https://res.cloudinary.com/demo/image/upload/webp.webp', 'public_id': 'miraki/ninos/webp'},
        ]):
            png = self.client.post('/api/v1/children/ninos/', {
                'nombre': 'PNG',
                'foto': image_file(name='photo.png', image_format='PNG', content_type='image/png'),
            }, format='multipart')
            webp = self.client.post('/api/v1/children/ninos/', {
                'nombre': 'WEBP',
                'foto': image_file(name='photo.webp', image_format='WEBP', content_type='image/webp'),
            }, format='multipart')

        self.assertEqual(png.status_code, status.HTTP_201_CREATED)
        self.assertEqual(webp.status_code, status.HTTP_201_CREATED)

    def test_create_nino_rejects_invalid_mime_and_oversized_photo(self):
        self.client.force_authenticate(self.user_a)

        invalid = self.client.post('/api/v1/children/ninos/', {
            'nombre': 'Gif',
            'foto': image_file(name='photo.gif', image_format='PNG', content_type='image/gif'),
        }, format='multipart')
        oversized = self.client.post('/api/v1/children/ninos/', {
            'nombre': 'Grande',
            'foto': SimpleUploadedFile('large.jpg', b'x' * (5 * 1024 * 1024 + 1), content_type='image/jpeg'),
        }, format='multipart')

        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(oversized.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('foto', invalid.data)
        self.assertIn('foto', oversized.data)

    def test_admin_centro_cannot_create_nino_with_photo(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.post('/api/v1/children/ninos/', {
            'nombre': 'Nope',
            'foto': image_file(),
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_compensates_uploaded_photo_when_db_fails(self):
        self.client.force_authenticate(self.user_a)
        self.client.raise_request_exception = False

        with patch('apps.children.services.upload_image', return_value={
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/new.jpg',
            'public_id': 'miraki/ninos/new',
        }), patch('apps.children.services.delete_image') as delete, patch(
            'apps.children.services.record_action',
            side_effect=DatabaseError('boom'),
        ):
            response = self.client.post('/api/v1/children/ninos/', {
                'nombre': 'Falla',
                'foto': image_file(),
            }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        delete.assert_called_once_with('miraki/ninos/new')
        self.assertFalse(Nino.objects.filter(nombre='Falla').exists())

    def test_patch_without_photo_keeps_current_photo(self):
        nino = Nino.objects.create(
            id_tutor=self.tutor_a,
            nombre='Actual',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)

        response = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {'nombre': 'Actualizado'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertEqual(nino.nombre, 'Actualizado')
        self.assertEqual(nino.foto_url, 'https://res.cloudinary.com/demo/image/upload/old.jpg')
        self.assertEqual(nino.foto_public_id, 'miraki/ninos/old')

    def test_patch_with_new_photo_replaces_and_deletes_old_after_success(self):
        nino = Nino.objects.create(
            id_tutor=self.tutor_a,
            nombre='Actual',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)

        with patch('apps.children.services.upload_image', return_value={
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/new.jpg',
            'public_id': 'miraki/ninos/new',
        }), patch('apps.children.services.delete_image') as delete:
            response = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {
                'foto': image_file(),
            }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertEqual(nino.foto_url, 'https://res.cloudinary.com/demo/image/upload/new.jpg')
        self.assertEqual(nino.foto_public_id, 'miraki/ninos/new')
        delete.assert_called_once_with('miraki/ninos/old')

    def test_patch_compensates_new_photo_when_db_fails_and_keeps_old_photo(self):
        nino = Nino.objects.create(
            id_tutor=self.tutor_a,
            nombre='Actual',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)
        self.client.raise_request_exception = False

        with patch('apps.children.services.upload_image', return_value={
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/new.jpg',
            'public_id': 'miraki/ninos/new',
        }), patch('apps.children.services.delete_image') as delete, patch(
            'apps.children.services.record_action',
            side_effect=DatabaseError('boom'),
        ):
            response = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {
                'foto': image_file(),
            }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        delete.assert_called_once_with('miraki/ninos/new')
        nino.refresh_from_db()
        self.assertEqual(nino.foto_url, 'https://res.cloudinary.com/demo/image/upload/old.jpg')
        self.assertEqual(nino.foto_public_id, 'miraki/ninos/old')

    def test_patch_photo_other_tutor_nino_returns_404(self):
        other = Nino.objects.create(id_tutor=self.tutor_b, nombre='Ajeno')
        self.client.force_authenticate(self.user_a)

        response = self.client.patch(f'/api/v1/children/ninos/{other.pk}/', {
            'foto': image_file(),
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_rejects_invalid_photo(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Actual')
        self.client.force_authenticate(self.user_a)

        response = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {
            'foto': image_file(name='photo.gif', image_format='PNG', content_type='image/gif'),
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('foto', response.data)

    def test_patch_photo_registers_audit_without_public_id(self):
        nino = Nino.objects.create(
            id_tutor=self.tutor_a,
            nombre='Actual',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)

        with patch('apps.children.services.upload_image', return_value={
            'secure_url': 'https://res.cloudinary.com/demo/image/upload/new.jpg',
            'public_id': 'miraki/ninos/new',
        }), patch('apps.children.services.delete_image'):
            response = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {
                'foto': image_file(),
            }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit = Bitacora.objects.filter(tabla_afectada='nino', operacion='UPDATE').latest('id_bitacora')
        self.assertEqual(audit.datos_anteriores['foto_url'], 'https://res.cloudinary.com/demo/image/upload/old.jpg')
        self.assertEqual(audit.datos_nuevos['foto_url'], 'https://res.cloudinary.com/demo/image/upload/new.jpg')
        self.assertNotIn('foto_public_id', audit.datos_anteriores)
        self.assertNotIn('foto_public_id', audit.datos_nuevos)

    def test_tutor_owner_can_remove_photo(self):
        nino = Nino.objects.create(
            id_tutor=self.tutor_a,
            nombre='Actual',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)

        with patch('apps.children.services.delete_image') as delete:
            response = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-photo/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertIsNone(nino.foto_url)
        self.assertIsNone(nino.foto_public_id)
        delete.assert_called_once_with('miraki/ninos/old')

    def test_remove_photo_without_photo_is_idempotent_without_duplicate_audit(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Sin Foto')
        self.client.force_authenticate(self.user_a)

        response = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-photo/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Bitacora.objects.filter(tabla_afectada='nino', operacion='UPDATE').exists())

    def test_remove_photo_other_tutor_returns_404_and_admin_cannot_access(self):
        other = Nino.objects.create(
            id_tutor=self.tutor_b,
            nombre='Ajeno',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)
        other_response = self.client.post(f'/api/v1/children/ninos/{other.pk}/remove-photo/')

        self.client.force_authenticate(self.admin_user)
        admin_response = self.client.post(f'/api/v1/children/ninos/{other.pk}/remove-photo/')

        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(admin_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_photo_registers_audit_when_changed(self):
        nino = Nino.objects.create(
            id_tutor=self.tutor_a,
            nombre='Actual',
            foto_url='https://res.cloudinary.com/demo/image/upload/old.jpg',
            foto_public_id='miraki/ninos/old',
        )
        self.client.force_authenticate(self.user_a)

        with patch('apps.children.services.delete_image'):
            response = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-photo/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit = Bitacora.objects.get(tabla_afectada='nino', operacion='UPDATE')
        self.assertEqual(audit.datos_anteriores, {'foto_url': 'https://res.cloudinary.com/demo/image/upload/old.jpg'})
        self.assertEqual(audit.datos_nuevos, {'foto_url': None})
