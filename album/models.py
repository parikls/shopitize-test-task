import logging
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from tempfile import NamedTemporaryFile

import requests
from django.core.files import File
from django.db import models, transaction
from django.db.models import Max

from album.exceptions import ServiceException
from shopitize import settings
from shopitize.settings import TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, MEDIA_ROOT
from twitter.api import Api
from twitter.exceptions import TwitterException

logger = logging.getLogger(__name__)


class AlbumManager(models.Manager):
    def to_dict_all(self):
        return [album.to_dict() for album in self.prefetch_related("image_set").all()]

    def get_dict(self, pk):
        return self.prefetch_related("image_set").get(pk=pk).to_dict()


class AlbumServiceManager(models.Manager):
    def __init__(self):
        super().__init__()

        self.__twitter = None
        self.MAX_IMAGES_IN_ALBUM = 100

    def create_album(self, hashtag):
        """
        Create album from hashtag, and fill it with
        images parsed from twitter response
        :param hashtag: str - provided hashtag
        :return album: Album - newly created instance of Album
        """
        with transaction.atomic():
            logger.debug("Start album creation")

            album = Album.objects.create(hashtag=hashtag)
            _images = self._collect_images(album)

            # there are cases when one tweet contains multiple media
            # so we should remove extra images
            if len(_images) > self.MAX_IMAGES_IN_ALBUM:
                del _images[self.MAX_IMAGES_IN_ALBUM:]

            if settings.PERSIST_IMAGES_TO_DB:
                self.__populate_files_to_images(_images)

            Image.objects.bulk_create(_images)
            logger.debug("End album creation")
        return album

    def update_album(self, album):
        """
        Update images of existing album
        :param album: Album instance
        """
        # reverse images for correct ordering
        _images = list(album.image_set.all().reverse())
        _new_images = self._collect_images(album)
        _updated = False

        for image in _new_images:
            if image not in _images:
                _updated = True
                _images.append(image)

        if not _updated:
            raise ServiceException(msg="No new images", status_code=200)

        with transaction.atomic():
            logger.debug("Start album updating")
            _for_delete = []
            _for_create = []

            # reverse back after new photos parsed
            for i, image in enumerate(reversed(_images)):

                # image.pk indicates that image is already persist in database.
                # collect list of new images, which are not currently persists in database
                # and list of old images for removing, because they are not fit to album size
                if i < self.MAX_IMAGES_IN_ALBUM and not image.pk:
                    _for_create.append(image)
                elif i >= self.MAX_IMAGES_IN_ALBUM and image.pk:
                    _for_delete.append(image.pk)

            if settings.PERSIST_IMAGES_TO_DB:
                self.__populate_files_to_images(_for_create)

            # bulk operations for creation and updating
            Image.objects.bulk_create(_for_create)
            Image.objects.filter(pk__in=_for_delete).delete()

            logger.debug("Created image instances: %s" % _for_create)
            logger.debug("Deleted PK of images: %s" % _for_delete)

        return album

    def _collect_images(self, album):
        """
        Return list of collected Image instances
        :param album: Album instance
        :return List of Image instances fetched from twitter response
        """

        self.__init_twitter_api()

        logger.debug("Start image collecting")
        params = dict(
            q="%s filter:images" % album.hashtag,
            result_type="recent",
            count=self.MAX_IMAGES_IN_ALBUM
        )
        _since_id = album.get_max_twitter_id()
        if _since_id:
            params["since_id"] = _since_id

        logger.debug("Params for twitter request=%s" % params)
        try:
            twitter_response = self.__twitter.search(params=params)
        except TwitterException as exc:
            logger.error("Exception in twitter request. %s" % exc.msg)
            raise ServiceException("Could not obtain data from Twitter", status_code=503)

        if len(twitter_response.statuses) == 0:
            raise ServiceException("No images found for hashtag %s" % album.hashtag, status_code=400)

        images = []
        for status in twitter_response:
            for media in status.extended_entity.media:
                image = Image(album=album, twitter_id=media.id, url=media.url, media_url=media.media_url)
                try:
                    # external url represents url on some external resource
                    # if they are equal - media is also equal, and we need
                    # this property to perform correct duplication removing
                    image.external_url = status.entity.url[0].expanded_url
                except IndexError:
                    image.external_url = None

                if image not in images:
                    # avoid duplicates in response
                    images.append(image)
        logger.debug("Finish images collecting. Images=%s" % images)
        return images

    def __populate_files_to_images(self, image_list):
        """
        Method to download images from
        each of Image instance in image_list

        :param image_list: List with Image instances
        """

        logger.debug("start populating of files to Image instances")

        # Assuming that downloading - is a network I/O - threads will be good enough here
        with ThreadPoolExecutor() as pool:
            # create future objects for images, that doesn't have image file instance on them
            futures = {pool.submit(image.download_image) for image in image_list if not image.image}
            for future in as_completed(futures):
                if future.exception():
                    logger.error("Error while downloading image. Future exception: %s "
                                 % future.exception())

                    # re-raise exception to reflect it in response
                    raise ServiceException("Error occurred while downloading photo =( ", status_code=500)
        logger.debug("end populating of files to Image instances")

    def __init_twitter_api(self):
        if not self.__twitter:
            logger.debug("Initializing twitter API")
            try:
                self.__twitter = Api(consumer_key=TWITTER_CONSUMER_KEY, consumer_secret=TWITTER_CONSUMER_SECRET)
            except Exception:
                raise ServiceException(msg="Could not connect to Twitter", status_code=503)


class Album(models.Model):
    objects = AlbumManager()
    service = AlbumServiceManager()

    hashtag = models.CharField(max_length=255)

    def to_dict(self):
        _images = [image.to_dict() for image in self.image_set.all()]
        return dict(
            pk=self.pk,
            hashtag=self.hashtag,
            images=_images,
            preview_image=random.choice(_images)
        )

    def get_max_twitter_id(self):
        return self.image_set.aggregate(Max("twitter_id")).get("twitter_id__max")

    def get_absolute_url(self):
        return "/api/album/%i" % self.id

    def __str__(self):
        return "Album %s" % self.hashtag

    class Meta:
        verbose_name = "Album"
        verbose_name_plural = "Album"


class Image(models.Model):
    album = models.ForeignKey(to=Album)
    twitter_id = models.IntegerField()
    url = models.URLField()
    media_url = models.URLField(blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True, upload_to='.')

    def to_dict(self):
        image = dict(
            twitter_id=self.twitter_id,
            url=self.url
        )
        if settings.PERSIST_IMAGES_TO_DB:
            image["media_url"] = self.image.url if self.image else self.media_url
        else:
            image["media_url"] = self.media_url
        return image

    def download_image(self):
        """
        Method downloads image file from media_url, creates temp file
        and set it on instance using django File wrapper
        """
        logger.debug(
            "Downloading image for instance with twitter_id=%s from url=%s" % (self.twitter_id, self.media_url))
        response = requests.get(self.media_url, stream=True)
        if response.status_code == 200:
            temp_file = NamedTemporaryFile(dir=MEDIA_ROOT, delete=True)
            for block in response.iter_content(1024 * 8):
                if not block:
                    break
                temp_file.write(block)
            temp_file.flush()
            self.image = File(temp_file, os.path.basename(temp_file.name))

            logger.debug("Image downloading finished for instance with twitter_id=%s" % self.twitter_id)

    def __str__(self):
        return "twitter_id: %d. twitter_url: %s. media_url: %s" % (self.twitter_id, self.url, self.media_url)

    def __eq__(self, other):
        """
        Fields which involved in comparison
        represent uniqueness of Image against Twitter
        """
        return (self.url == other.url or
                self.media_url == other.media_url or
                self.external_url == other.external_url)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Image"
        ordering = ['-twitter_id']
