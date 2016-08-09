from django.conf.urls import url
from album.views import *


# API URLs
urlpatterns = [
    url(r'^api/album/$', ApiAlbumView.as_view()),
    url(r'^api/album/(?P<pk>\d+)/$', ApiAlbumDetailsView.as_view()),
    url(r'^api/csrf/$', get_csrf_token)

]

# Template URLs
urlpatterns += [
    url(r'^album/(?P<pk>\d+)/$', TemplateAlbumDetailsView.as_view(), name='album_details'),
    url(r'^$', TemplateAlbumListView.as_view(), name="album"),
]


