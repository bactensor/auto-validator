from django.contrib import admin
from rest_framework.authtoken.admin import TokenAdmin

from auto_validator.validator_manager.models import (
    ExternalHotkey,
    Subnet,
    Validator,
    ValidatorHotkey,
)

TokenAdmin.raw_id_fields = ["user"]


class ValidatorManagerAdminSite(admin.AdminSite):
    site_header = "validator_manager Administration"
    site_title = "validator_manager"
    index_title = "Welcome to validator_manager Administration"


admin_site = ValidatorManagerAdminSite(name="validator_manager_admin")


class SubnetAdmin(admin.ModelAdmin):
    search_fields = ("codename",)
    list_display = ("codename",)


admin_site.register(Subnet, SubnetAdmin)


class ValidatorHotkeyInline(admin.TabularInline):
    model = ValidatorHotkey
    extra = 1
    fields = (
        "external_hotkey",
        "is_default",
    )
    autocomplete_fields = ("external_hotkey",)


class ValidatorHotkeyInlineForExternalHotkey(admin.StackedInline):
    model = ValidatorHotkey
    extra = 0
    max_num = 1
    fields = (
        "validator",
        "is_default",
    )
    autocomplete_fields = ("validator",)
    verbose_name = "Validator"
    verbose_name_plural = "Select Validator"


class ValidatorAdmin(admin.ModelAdmin):
    list_display = (
        "long_name",
        "last_stake",
        "default_hotkey_display",
    )
    search_fields = (
        "long_name",
        "short_name",
    )  # Added 'short_name' here to cover both fields in autocomplete
    inlines = [ValidatorHotkeyInline]

    def default_hotkey_display(self, obj):
        default_hotkey = obj.default_hotkey
        return default_hotkey.name if default_hotkey else "N/A"

    default_hotkey_display.short_description = "Default Hotkey"


admin_site.register(Validator, ValidatorAdmin)


class ExternalHotkeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "hotkey",
        "subnet",
        "validator_display",
    )
    search_fields = ("name", "hotkey", "subnet__name")  # Added 'subnet__name' to support the ForeignKey in autocomplete
    list_filter = ("subnet",)
    autocomplete_fields = ("subnet",)
    inlines = [ValidatorHotkeyInlineForExternalHotkey]

    def validator_display(self, obj):
        validator = obj.validator
        return validator.long_name if validator else "N/A"

    validator_display.short_description = "Validator"


admin_site.register(ExternalHotkey, ExternalHotkeyAdmin)
