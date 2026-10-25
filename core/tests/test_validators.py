from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import SimpleTestCase

from core.forms import https_url_formfield
from core.validators import MAX_UPLOAD_SIZE, validate_upload_size


class UploadSizeTests(SimpleTestCase):
    def test_file_of_exactly_five_megabytes_is_accepted(self):
        validate_upload_size(SimpleUploadedFile("support.pdf", b"0" * MAX_UPLOAD_SIZE))

    def test_larger_file_is_refused(self):
        with self.assertRaisesMessage(ValidationError, "5 Mo"):
            validate_upload_size(SimpleUploadedFile("support.pdf", b"0" * (MAX_UPLOAD_SIZE + 1)))

    def test_file_already_stored_is_not_read_again(self):
        class StoredFile:
            _committed = True

            @property
            def size(self):
                raise AssertionError("le stockage ne doit pas être relu")

        validate_upload_size(StoredFile())


class HttpsUrlFormfieldTests(SimpleTestCase):
    def test_url_without_protocol_becomes_https(self):
        field = https_url_formfield(models.URLField())

        self.assertEqual(field.clean("docs.djangoproject.com"), "https://docs.djangoproject.com")

    def test_other_fields_are_unchanged(self):
        self.assertIsInstance(https_url_formfield(models.CharField(max_length=10)), forms.CharField)
