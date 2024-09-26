from rest_framework import mixins, parsers, routers, viewsets
from rest_framework.permissions import AllowAny

from auto_validator.core.models import UploadedFile
from auto_validator.core.serializers import UploadedFileSerializer

from .authentication import HotkeyAuthentication
from .utils.bot import trigger_bot_send_message


class FilesViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UploadedFileSerializer
    parser_classes = [parsers.MultiPartParser]
    queryset = UploadedFile.objects.all()

    authentication_classes = [HotkeyAuthentication]
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        uploaded_file = serializer.save()
        note = self.request.headers.get("Note")
        channel_name = self.request.headers.get("SubnetID")
        realm = self.request.headers.get("Realm")
        file_url = uploaded_file.get_full_url(self.request)
        trigger_bot_send_message(
            channel_name=channel_name, message=(f"{note}\n" f"New validator logs:\n" f"{file_url}"), realm=realm
        )


class APIRootView(routers.DefaultRouter.APIRootView):
    description = "api-root"


class APIRouter(routers.DefaultRouter):
    APIRootView = APIRootView


router = APIRouter()
router.register(r"files", FilesViewSet, basename="file")
