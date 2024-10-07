import logging
import pathlib

from django.conf import settings
from rest_framework import mixins, parsers, routers, status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from auto_validator.core.models import Hotkey, Server, UploadedFile, ValidatorInstance
from auto_validator.core.serializers import UploadedFileSerializer
from auto_validator.core.utils.utils import get_user_ip

from .authentication import HotkeyAuthentication
from .utils.bot import trigger_bot_send_message
from .utils.utils import get_dumper_commands

SUBNETS_CONFIG_PATH = pathlib.Path(settings.LOCAL_SUBNETS_SCRIPTS_PATH) / "subnets.yaml"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


class DumperCommandsViewSet(viewsets.ViewSet):
    parser_classes = [parsers.MultiPartParser]
    permission_classes = [AllowAny]

    def list(self, request):
        subnet_identifier = request.headers.get("SubnetID")
        if not subnet_identifier:
            return Response({"error": "SubnetID is required"}, status=status.HTTP_400_BAD_REQUEST)

        dumper_commands = get_dumper_commands(subnet_identifier, SUBNETS_CONFIG_PATH)
        if dumper_commands is not None:
            logger.info(f"SubnetID: {subnet_identifier}, dumper_commands: {dumper_commands}")
            return Response(dumper_commands)
        else:
            logger.error(f"SubnetID: {subnet_identifier} not found")
            return Response({"error": "SubnetID not found"}, status=status.HTTP_404_NOT_FOUND)


class APIRootView(routers.DefaultRouter.APIRootView):
    description = "api-root"


class APIRouter(routers.DefaultRouter):
    APIRootView = APIRootView


router = APIRouter()
router.register(r"files", FilesViewSet, basename="file")
router.register(r"commands", DumperCommandsViewSet, basename="commands")
