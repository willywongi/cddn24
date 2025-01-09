from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

import album.views

urlpatterns = [
    path("", album.views.claim, name="claim"),
    path("<signature>/claimed", album.views.claimed, name="claimed"),
    path("<signature>/validate", album.views.validate, name="validate"),
    path("<signature>/not-valid", album.views.not_valid, name="not_valid"),
    path("<signature>/play", album.views.read, name="play"),
    path("<signature>/download", album.views.download, name="download"),
    path("set-theme", album.views.set_theme, name="set_theme"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
