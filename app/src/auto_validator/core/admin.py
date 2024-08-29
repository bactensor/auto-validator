from django.contrib import admin  # noqa
from django.contrib.admin import register  # noqa
from rest_framework.authtoken.admin import TokenAdmin

from auto_validator.core.models import UploadedFile

admin.site.site_header = "auto_validator Administration"
admin.site.site_title = "auto_validator"
admin.site.index_title = "Welcome to auto_validator Administration"

TokenAdmin.raw_id_fields = ["user"]


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("file_name", "file_size", "user", "created_at")
    list_filter = ("user", "created_at", "file_size")
    search_fields = ("file_name",)
