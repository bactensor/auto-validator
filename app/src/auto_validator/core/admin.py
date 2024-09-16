from django.contrib import admin
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import redirect, render
from django.urls import path, reverse
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
from auto_validator.core.plugins.linode_plugin import LinodePlugin
from auto_validator.core.plugins.paperspace_plugin import PaperspacePlugin
from auto_validator.core.plugins.plugin_manager import PluginManager
from auto_validator.core.utils.utils import fetch_and_compare_subnets

plugin_manager = PluginManager()
plugin_manager.register_plugin("Linode", LinodePlugin)
plugin_manager.register_plugin("Paperspace", PaperspacePlugin)


admin.site.site_header = "auto_validator Administration"
admin.site.site_title = "auto_validator"
admin.site.index_title = "Welcome to auto_validator Administration"

TokenAdmin.raw_id_fields = ["user"]


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("file_name", "file_size", "hotkey", "description", "created_at")
    list_filter = ("hotkey", "created_at", "file_size")
    search_fields = ("file_name",)


@admin.register(Subnet)
class SubnetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "mainnet_id",
        "testnet_id",
        "owner_nick",
        "owner_id",
        "maintainers_id",
        "registered_networks",
    )
    search_fields = ("name", "slots__netuid")

    def create_server(self, request, queryset):
        subnet = queryset.first()
        return redirect("admin:select_provider", subnet_id=subnet.id)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync-subnets/", self.admin_site.admin_view(self.sync_subnet), name="sync_subnets"),
            path(
                "<int:subnet_id>/select-provider/",
                self.admin_site.admin_view(self.select_provider_view),
                name="select_provider",
            ),
            path(
                "<int:subnet_id>/<str:provider>/create-server/",
                self.admin_site.admin_view(self.create_server_view),
                name="create_server",
            ),
        ]
        return custom_urls + urls

    def sync_subnet(self, request):
        return fetch_and_compare_subnets(request)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["sync_subnets_url"] = reverse("admin:sync_subnets")
        return super().changelist_view(request, extra_context=extra_context)

    def select_provider_view(self, request, subnet_id):
        # subnet = Subnet.objects.get(id=subnet_id)
        if request.method == "POST":
            provider = request.POST.get("provider")
            self.message_user(request, f"Provider selected: {provider}")
            return redirect("admin:create_server", provider=provider, subnet_id=subnet_id)
        context = {"providers": plugin_manager.get_registered_plugins()}
        return render(request, "admin/select_provider.html", context)

    def create_server_view(self, request, subnet_id, provider):
        # subnet = self.get_object(request, subnet_id)
        plugin = plugin_manager.get_plugin(provider)
        if request.method == "POST":
            form_data = request.POST.copy()
            form_data["api_key"] = "1234"
            form_info = {}
            for key, value in form_data.items():
                form_info[key] = value
            print(form_info)
            plugin.create_machine(form_info)
            return redirect("admin:core_subnet_changelist")
        context = {"fields": plugin.get_required_fields(), "list_of_machines": plugin.list_available_machines()}
        return render(request, "admin/create_server.html", context)

    actions = ["create_server"]


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
