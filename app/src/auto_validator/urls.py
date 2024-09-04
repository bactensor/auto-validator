from django.conf import settings
from django.conf.urls.static import static
from django.contrib.admin.sites import site
from django.urls import include, path
from fingerprint.views import FingerprintView

urlpatterns = [
    path("admin/", site.urls),
    path("redirect/", FingerprintView.as_view(), name="fingerprint"),
    path("", include("django.contrib.auth.urls")),
    path("", include("auto_validator.core.urls")),
    path("webhook/", include("auto_validator.webhook.urls")),
]

if settings.DEBUG:
    # serving media files from same domain is dangerous and should never be the case in production
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))

if settings.DEBUG_TOOLBAR:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
