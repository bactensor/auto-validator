from django.contrib import admin
from django.db.models import Case, IntegerField, Value, When
from rest_framework.authtoken.admin import TokenAdmin

from auto_validator.core.models import (
    Hotkey,
    Operator,
    Server,
    Subnet,
    SubnetSlot,
    UploadedFile,
    ValidatorInstance,
)

admin.site.site_header = "auto_validator Administration"
admin.site.site_title = "auto_validator"
admin.site.index_title = "Welcome to auto_validator Administration"

TokenAdmin.raw_id_fields = ["user"]


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("file_name", "file_size", "user", "created_at")
    list_filter = ("user", "created_at", "file_size")
    search_fields = ("file_name",)


@admin.register(Subnet)
class SubnetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "registered_networks",
    )
    search_fields = ("name", "slots__netuid")


@admin.register(SubnetSlot)
class SubnetSlotAdmin(admin.ModelAdmin):
    list_display = (
        "subnet",
        "blockchain",
        "netuid",
        "is_registered",
        "max_registration_price_RAO",
        "registration_block",
        "deregistration_block",
    )
    search_fields = ("subnet__name", "netuid")
    list_filter = ("blockchain",)
    list_select_related = ("subnet", "registration_block", "deregistration_block")

    def registration_block(self, obj):
        return obj.registration_block.serial_number if obj.registration_block else "N/A"

    registration_block.short_description = "Registration Block"

    def deregistration_block(self, obj):
        return obj.deregistration_block.serial_number if obj.deregistration_block else "N/A"

    deregistration_block.short_description = "Deregistration Block"

    def max_registration_price_RAO(self, obj):
        return f"{obj.maximum_registration_price} RAO"

    def is_registered(self, obj):
        return obj.registration_block is not None and obj.deregistration_block is None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            is_registered_sort=Case(
                When(registration_block__isnull=False, deregistration_block__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        return qs.order_by("blockchain", "netuid")

    is_registered.boolean = True
    is_registered.admin_order_field = "is_registered_sort"
    is_registered.short_description = "Is Registered"


@admin.register(ValidatorInstance)
class ValidatorInstanceAdmin(admin.ModelAdmin):
    list_display = ("subnet_slot", "hotkey", "last_updated", "status", "server", "created_at")
    search_fields = ("hotkey", "subnet_slot__subnet__name", "server__name")


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("name", "ip_address", "subnet_slot", "validatorinstance_status", "description", "created_at")
    search_fields = ("name", "ip_address", "validator_instances__subnet_slot__subnet__name")

    def subnet_slot(self, obj):
        return obj.validator_instances.subnet_slot if obj.validator_instances else "N/A"

    def validatorinstance_status(self, obj):
        return getattr(obj.validator_instances, "status", False)

    validatorinstance_status.boolean = True

    list_select_related = ("validator_instances", "validator_instances__subnet_slot")


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "discord_id")
    search_fields = ("name", "discord_id")


@admin.register(Hotkey)
class HotkeyAdmin(admin.ModelAdmin):
    list_display = ("hotkey", "is_mother")
    search_fields = ("hotkey",)
