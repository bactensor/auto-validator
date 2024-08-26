from rest_framework import mixins, parsers, routers, viewsets

from auto_validator.core.models import UploadedFile
from auto_validator.core.serializers import UploadedFileSerializer


class FilesViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UploadedFileSerializer
    parser_classes = [parsers.MultiPartParser]

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class APIRootView(routers.DefaultRouter.APIRootView):
    description = "api-root"


class APIRouter(routers.DefaultRouter):
    APIRootView = APIRootView


router = APIRouter()
router.register(r"files", FilesViewSet, basename="file")
