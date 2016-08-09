from django.conf.urls import url, include
from django.contrib import admin
from django.views.static import serve

from shopitize import settings


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('album.urls', namespace='album')),
]

if settings.DEBUG and settings.PERSIST_IMAGES_TO_DB:
    urlpatterns += url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
