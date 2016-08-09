import os
from tempfile import NamedTemporaryFile
from unittest.mock import patch, Mock

from django.core.files import File
from django.test import TestCase, Client, override_settings

from album.exceptions import ServiceException
from album.models import Image, Album
from album.util import is_valid_hashtag
from shopitize.settings import BASE_DIR, MEDIA_ROOT
from twitter.exceptions import TwitterException

TEST_MEDIA_ROOT = os.path.join(BASE_DIR, 'media', 'test')


@override_settings(PERSIST_IMAGES_TO_DB=False)
@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BaseTestCases(TestCase):
    def setUp(self):
        if not os.path.isdir(MEDIA_ROOT):
            os.mkdir(MEDIA_ROOT)
        if not os.path.isdir(TEST_MEDIA_ROOT):
            os.mkdir(TEST_MEDIA_ROOT)
        self.client = Client()
        _temp_file = NamedTemporaryFile(dir=TEST_MEDIA_ROOT, delete=True)
        _temp_file.write(b"0")
        _temp_file.flush()
        self._album = Album.objects.create(hashtag="#hashtag")
        self._image = Image.objects.create(
            twitter_id=1,
            url="https://twitter.com/1/",
            media_url="https://twitter.com/media/1/",
            image=File(_temp_file),
            album=self._album
        )

    def tearDown(self):
        for file in os.listdir(TEST_MEDIA_ROOT):
            os.unlink(os.path.join(TEST_MEDIA_ROOT, file))


class ViewTestCases(BaseTestCases):
    def test_api_get_all(self):
        response = self.client.get("/api/album/")
        response_json = response.json()
        expected_json = {
            "message": None,
            "data": Album.objects.to_dict_all()}
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 200)

    def test_api_get_by_pk_success(self):
        response = self.client.get("/api/album/1/")
        response_json = response.json()
        expected_json = {
            "message": None,
            "data": Album.objects.get_dict(pk=1)
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 200)

    def test_api_get_by_pk_does_not_exists(self):
        response = self.client.get("/api/album/2/")
        response_json = response.json()
        expected_json = {
            "message": "No such album",
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 404)

    def test_api_create_album_no_hashtag_provided(self):
        response = self.client.post("/api/album/", data={"hashtag": ""})
        response_json = response.json()
        expected_json = {
            "message": "Parameter hashtag was not found in request",
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 400)

    def test_api_create_album_invalid_hashtag(self):
        response = self.client.post("/api/album/", data={"hashtag": "not_a_hashtag"})
        response_json = response.json()
        expected_json = {
            "message": 'Hashtag "not_a_hashtag" must starts with "#" sign',
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 400)

    @patch("album.views.Album.service")
    def test_api_create_album_service_error(self, album_service):
        album_service.create_album = Mock(side_effect=ServiceException("service exception", 400))

        response = self.client.post("/api/album/", data={"hashtag": "#hashtag"})
        response_json = response.json()
        expected_json = {
            "message": 'service exception',
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 400)

    @patch("album.models.twitter")
    def test_api_create_album_twitter_error(self, twitter_service):
        twitter_service.search = Mock(side_effect=TwitterException)

        response = self.client.post("/api/album/", data={"hashtag": "#hashtag"})
        response_json = response.json()
        expected_json = {
            "message": 'Could not obtain data from Twitter',
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 503)

    @patch("album.views.Album.service")
    def test_api_create_album_success(self, album_service):
        album = Album.objects.get(pk=1)
        album_service.create_album = Mock(return_value=album)

        response = self.client.post("/api/album/", data={"hashtag": "#hashtag"})
        response_json = response.json()

        expected_json = {
            "message": "Successfully created new album for hashtag #hashtag",
            "data": album.to_dict()
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 201)

    def test_api_refresh_album_does_not_exists(self):
        response = self.client.patch("/api/album/2/")
        response_json = response.json()
        expected_json = {
            "message": "No such album",
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 404)

    @patch("album.views.Album.service")
    def test_api_refresh_no_new_images(self, album_service):
        album_service.update_album = Mock(side_effect=ServiceException("No new images", 200))

        response = self.client.patch("/api/album/1/")
        response_json = response.json()
        expected_json = {
            "message": "No new images",
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 200)

    @patch("album.views.Album.service")
    def test_api_refresh_service_error(self, album_service):
        album_service.update_album = Mock(side_effect=ServiceException("service_exception", 400))

        response = self.client.patch("/api/album/1/")
        response_json = response.json()
        expected_json = {
            "message": "service_exception",
            "data": None
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 400)

    @patch("album.views.Album.service")
    def test_api_refresh_success(self, album_service):
        album = Album.objects.get(pk=1)
        album_service.update_album = Mock(return_value=album)

        response = self.client.patch("/api/album/1/", data={"pk": 1})
        response_json = response.json()
        expected_json = {
            "message": "Successfully updated album with hashtag #hashtag",
            "data": album.to_dict()
        }
        self.assertDictEqual(expected_json, response_json)
        self.assertEqual(response.status_code, 200)

    def test_template_get_all(self):
        response = self.client.get("/")
        self.assertTemplateUsed("index.html")
        self.assertListEqual(response.context["albums"], Album.objects.to_dict_all())

    def test_template_get_by_pk_success(self):
        response = self.client.get("/album/1/")
        self.assertTemplateUsed(response, "details.html")
        self.assertDictEqual(response.context["album"], Album.objects.get_dict(pk=1))

    def test_template_get_by_pk_does_not_exists(self):
        response = self.client.get("/album/2/")
        self.assertEqual(response.status_code, 404)

    @patch("album.views.Album.service")
    def test_template_create_album_success(self, album_service):
        album = Album.objects.get(pk=1)
        album_service.create_album = Mock(return_value=album)

        response = self.client.post("/", data={"hashtag": "#otherhashtag"}, follow=True)
        self.assertTemplateUsed(response, "details.html")

    def test_template_create_album_validation_error(self):
        response = self.client.post("/", data={"hashtag": "not_a_hashtag"})
        self.assertTemplateUsed(response, "index.html")
        self.assertListEqual(Album.objects.to_dict_all(), response.context["albums"])
        self.assertEqual('Hashtag "not_a_hashtag" must starts with "#" sign',
                         response.context["form"]["hashtag"].errors)

    @patch("album.views.Album.service")
    def test_template_create_album_service_error(self, album_service):
        album_service.create_album = Mock(side_effect=ServiceException("service exception"))

        response = self.client.post("/", data={"hashtag": "#valid_hashtag"})
        self.assertTemplateUsed(response, "index.html")
        self.assertListEqual(Album.objects.to_dict_all(), response.context["albums"])
        self.assertEqual("service exception", response.context["error"])

    @patch("album.views.Album.service")
    def test_template_refresh_success(self, album_service):
        album = Album.objects.get(pk=1)
        album_service.update_album = Mock(return_value=album)

        response = self.client.post("/album/1/", follow=True)
        self.assertTemplateUsed(response, "details.html")
        self.assertDictEqual(album.to_dict(), response.context["album"])

    def test_template_refresh_does_not_exists(self):
        response = self.client.get("/album/2/refresh/")
        self.assertEqual(response.status_code, 404)

    @patch("album.views.Album.service")
    def test_template_refresh_service_error(self, album_service):
        album_service.update_album = Mock(side_effect=ServiceException("service exception"))

        response = self.client.post("/album/1/")
        self.assertTemplateUsed(response, "details.html")
        self.assertEqual(response.context["error"], "service exception")
        self.assertEqual(response.context["album"], Album.objects.get_dict(pk=1))


class UtilTestCases(TestCase):
    def test_is_valid_hashtag(self):
        valid, message = is_valid_hashtag("not_valid")
        self.assertFalse(valid)
        self.assertEqual('Hashtag "not_valid" must starts with "#" sign', message)
        valid, message = is_valid_hashtag("#another one not valid")
        self.assertFalse(valid)
        self.assertEqual('Hashtag "#another one not valid" cannot contain whitespaces', message)
        valid, message = is_valid_hashtag("#valid")
        self.assertTrue(valid)
        self.assertIsNone(message)
