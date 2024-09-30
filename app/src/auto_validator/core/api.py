from rest_framework import mixins, parsers, routers, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny

from auto_validator.core.models import Hotkey, Server, UploadedFile, ValidatorInstance
from auto_validator.core.serializers import UploadedFileSerializer
from auto_validator.core.utils.utils import get_user_ip

from .authentication import HotkeyAuthentication
from .utils.bot import trigger_bot_send_message


class FilesViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UploadedFileSerializer
    parser_classes = [parsers.MultiPartParser]
    authentication_classes = [HotkeyAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        hotkey_str = self.request.headers.get("Hotkey")
        try:
            hotkey = Hotkey.objects.get(hotkey=hotkey_str)
        except Hotkey.DoesNotExist:
            return []
        return UploadedFile.objects.filter(hotkey=hotkey).order_by("id")

    def perform_create(self, serializer):
        note = self.request.headers.get("Note")
        hotkey_str = self.request.headers.get("Hotkey")
        channel_name = self.request.headers.get("SubnetID")
        realm = self.request.headers.get("Realm")
        ip_address = get_user_ip(self.request)
        try:
            hotkey = Hotkey.objects.get(hotkey=hotkey_str)
            server = Server.objects.get(ip_address=ip_address)
            subnetslot = ValidatorInstance.objects.get(hotkey=hotkey, server=server).subnet_slot
        except ValidatorInstance.DoesNotExist:
            raise AuthenticationFailed("Invalid Hotkey")
        uploaded_file = serializer.save(
            meta_info={
                "note": note,
                "hotkey": hotkey_str,
                "subnet_name": subnetslot.subnet.name,
                "netuid": subnetslot.netuid,
            }
        )
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
