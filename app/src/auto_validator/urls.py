from django.conf import settings
from django.contrib.admin.sites import site
from django.urls import include, path
from fingerprint.views import FingerprintView

urlpatterns = [
    path("admin/", site.urls),
    path("redirect/", FingerprintView.as_view(), name="fingerprint"),
    path("", include("django.contrib.auth.urls")),
]

if settings.DEBUG_TOOLBAR:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
