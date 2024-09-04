from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken.views import obtain_auth_token
from . import views

from .api import router

urlpatterns = [
    path(
        "api/",
        RedirectView.as_view(pattern_name="swagger-ui", permanent=False),
        name="api_index",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/v1/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    path("api-token-auth/", obtain_auth_token, name="api-token-auth"),
    path('', views.webhook, name='webhook'),
]
