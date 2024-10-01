import yaml
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

YAML_FILE_PATH = settings.LOCAL_SUBNETS_SCRIPTS_PATH + "/subnets.yaml"


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
            return Response({"error": "subnet_identifier is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with open(YAML_FILE_PATH) as file:
                data = yaml.safe_load(file)
                if subnet_identifier in data:
                    return Response(data[subnet_identifier].get("dumper_commands", []))
                else:
                    return Response({"error": "subnet_identifier not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NormalizedCodenameViewSet(viewsets.ViewSet):
    parser_classes = [parsers.MultiPartParser]
    permission_classes = [AllowAny]

    def list(self, request):
        subnet_identifier = request.headers.get("SubnetID")
        if not subnet_identifier:
            return Response({"error": "subnet_identifier is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with open(YAML_FILE_PATH) as file:
                data = yaml.safe_load(file)
                codename_lower = subnet_identifier.lower()
                for normalized_codename, sn_config in data.items():
                    codenames = sn_config.get("codename_list", [])
                    if codename_lower in map(str.lower, codenames):
                        return Response(normalized_codename)
                return Response({"error": "subnet_identifier not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APIRootView(routers.DefaultRouter.APIRootView):
    description = "api-root"


class APIRouter(routers.DefaultRouter):
    APIRootView = APIRootView


router = APIRouter()
router.register(r"files", FilesViewSet, basename="file")
router.register(r"commands", DumperCommandsViewSet, basename="commands")
router.register(r"codename", NormalizedCodenameViewSet, basename="codename")
