import logging

from django.http import Http404
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View

from album.exceptions import ServiceException
from album.forms import AlbumForm
from album.models import Album
from album.util import json_response, is_valid_hashtag

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Should be called to obtain Django CSRF Token
    """
    return json_response(status_code=200)


class ApiAlbumView(View):
    def get(self, request):
        logger.debug("ApiAlbumView. GET. STATUS=200. Returning all albums")
        return json_response(data=Album.objects.to_dict_all(), status_code=200)

    def post(self, request):

        logger.debug("ApiAlbumView. POST. Start album creation")
        _hashtag = request.POST.get("hashtag")
        if not _hashtag:
            logger.debug("ApiAlbumView. POST. STATUS=400. Could not parse hashtag from request=%s" % request)
            return json_response(message="Parameter hashtag was not found in request", status_code=400)

        is_valid, message = is_valid_hashtag(_hashtag)
        if is_valid:
            try:
                album = Album.service.create_album(hashtag=_hashtag)
                logger.debug("ApiAlbumView. POST. STATUS=201. Successfully created new album with pk=%s" % album.pk)
                return json_response(data=album.to_dict(), status_code=201,
                                     message="Successfully created new album for hashtag %s" % _hashtag,
                                     headers={"Location": request.build_absolute_uri(album.get_absolute_url())})
            except ServiceException as exc:
                logger.debug(
                    "ApiAlbumView. POST. STATUS=%s. Error while creating new album from hashtag=%s. exception=%s" %
                    (exc.status_code, _hashtag, exc.msg))
                return json_response(message=exc.msg, status_code=exc.status_code)

        # not valid hashtag
        logger.debug("ApiAlbumView. POST. STATUS=400. Hashtag %s is not valid" % _hashtag)
        return json_response(message=message, status_code=400)


class ApiAlbumDetailsView(View):
    def get(self, request, pk):
        try:
            return json_response(data=Album.objects.get_dict(pk=pk), status_code=200)
        except Album.DoesNotExist:
            logger.debug("ApiAlbumView. GET. STATUS=404. Album with pk=%s was not found" % pk)
            return json_response(message="No such album", status_code=404)

    def patch(self, request, pk):

        logger.debug("ApiAlbumRefreshView. PATCH. Start album updating. pk=%s" % pk)
        try:
            album = Album.objects.get(pk=pk)
        except Album.DoesNotExist:
            logger.debug("ApiAlbumRefreshView. PATCH. STATUS=404. Album with pk=%s was not found" % pk)
            return json_response(message="No such album", status_code=404)
        try:
            album = Album.service.update_album(album)
            logger.debug("ApiAlbumRefreshView. PATCH. STATUS=200. Album was updated. pk=%s" % pk)
            return json_response(data=album.to_dict(), status_code=200,
                                 message="Successfully updated album with hashtag %s" % album.hashtag)
        except ServiceException as exc:
            logger.debug(
                "ApiAlbumRefreshView. PATCH. STATUS=%s. Error while updating album with pk=%s. exception=%s" % (
                    exc.status_code, pk, exc.msg))
            return json_response(message=exc.msg, status_code=exc.status_code)


class TemplateAlbumListView(View):
    def get(self, request):
        logger.debug("TemplateAlbumView. GET. rendering index.html with all Albums")
        return render(request, 'index.html', context={'albums': Album.objects.to_dict_all()})

    def post(self, request):
        logger.debug("TemplateAlbumView. POST. request.POST=%s" % request.POST)
        form = AlbumForm(request.POST)
        if form.is_valid():
            hashtag = form.cleaned_data["hashtag"]
            try:
                album = Album.service.create_album(hashtag)
                logger.debug("TemplateAlbumView. POST. successfully created new album with pk=%s" % album.pk)
                return redirect("album:album_details", pk=album.pk)
            except ServiceException as exc:
                logger.debug("TemplateAlbumView. POST. Error while creating new album from hashtag=%s. exception=%s" %
                             (hashtag, exc.msg))
                return TemplateResponse(request, "index.html", context={"error": exc.msg})

        # form is not valid
        logger.debug("TemplateAlbumView. POST. form is not valid. rendering index.html")
        return TemplateResponse(request, "index.html", context={"form": form})


class TemplateAlbumDetailsView(View):
    def get(self, request, pk):
        try:
            logger.debug("TemplateAlbumDetailsView. GET. rendering details.html with album pk=%s" % pk)
            return render(request, 'details.html', context={'album': Album.objects.get_dict(pk=pk)})
        except Album.DoesNotExist:
            logger.debug("TemplateAlbumDetailsView. GET. Album does not exists.")
            raise Http404("Album does not exist")

    def post(self, request, pk):
        logger.debug("TemplateAlbumDetailsView. POST. pk=%s" % pk)
        try:
            album = Album.objects.get(pk=pk)
        except Album.DoesNotExist:
            logger.debug("TemplateAlbumDetailsView. POST. Album does not exists. pk=%s" % pk)
            raise Http404("Album does not exist")
        try:
            album = Album.service.update_album(album)
            logger.debug("TemplateAlbumDetailsView. POST. Album was updated. pk=%s" % pk)
            return redirect("album:album_details", pk=album.pk)
        except ServiceException as exc:
            logger.debug(
                "TemplateAlbumDetailsView. POST. Error while updating album with pk=%s. exception=%s" % (pk, exc.msg))
            return render(request, "details.html", context={"error": exc.msg, "album": album.to_dict()})
