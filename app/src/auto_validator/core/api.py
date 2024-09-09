from rest_framework import mixins, parsers, routers, viewsets
from rest_framework.response import Response

from auto_validator.core.models import UploadedFile
from auto_validator.core.serializers import UploadedFileSerializer
from auto_validator.core.utils.decorators import verify_signature_and_route_subnet


class FilesViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UploadedFileSerializer
    parser_classes = [parsers.MultiPartParser]

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user).order_by("id")

    @verify_signature_and_route_subnet
    def create(self, request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class APIRootView(routers.DefaultRouter.APIRootView):
    description = "api-root"


class APIRouter(routers.DefaultRouter):
    APIRootView = APIRootView


router = APIRouter()
router.register(r"files", FilesViewSet, basename="file")
