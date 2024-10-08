import secrets

from constance import config
from django.core.files.storage import default_storage
from rest_framework import serializers

from auto_validator.core.models import Hotkey, UploadedFile


def uploaded_file_size_validator(value):
    if value.size > config.API_UPLOAD_MAX_SIZE:
        raise serializers.ValidationError(f"File size must be < {config.API_UPLOAD_MAX_SIZE}B")


class UploadedFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, validators=[uploaded_file_size_validator])
    url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ("file_name", "file_size", "description", "url", "file")
        read_only_fields = ("file_name", "file_size", "created_at")

    def get_url(self, obj):
        request = self.context.get("request")
        if request:
            return obj.get_full_url(request)
        return obj.url

    def create(self, validated_data):
        file = validated_data.pop("file")
        meta_info = validated_data.pop("meta_info")
        # Generate a semi-random name for the file to prevent guessing the file name
        hotkey_str = meta_info["hotkey"]
        if not (hotkey := Hotkey.objects.get(hotkey=hotkey_str)):
            raise serializers.ValidationError("Invalid Hotkey")
        subnet_name = meta_info["subnet_name"]
        netuid = meta_info["netuid"]
        semi_random_name = f"{subnet_name}-{netuid}-{hotkey_str}-{secrets.token_urlsafe(32)}-{file.name}"
        filename_in_storage = default_storage.save(semi_random_name, file, max_length=4095)
        hotkey = Hotkey.objects.get(hotkey=hotkey_str)

        return UploadedFile.objects.create(
            hotkey=hotkey,
            file_name=file.name,
            file_size=file.size,
            description=meta_info["note"],
            storage_file_name=filename_in_storage,
            **validated_data,
        )
