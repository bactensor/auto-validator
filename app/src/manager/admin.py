from django.contrib import admin

from .models import Block, Hotkey, Operator, Server, Subnet, SubnetSlot, ValidatorInstance


# Admin Classes
@admin.register(Subnet)
class SubnetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "short_registration_indicator",
        "running_mainnet",
        "running_testnet",
    )
    search_fields = ("name",)

    def running_mainnet(self, obj):
        return obj.slots.filter(blockchain="mainnet").exists()
    running_mainnet.boolean = True
    running_mainnet.short_description = "Mainnet"

    def running_testnet(self, obj):
        return obj.slots.filter(blockchain="testnet").exists()
    running_testnet.boolean = True
    running_testnet.short_description = "Testnet"
    def short_registration_indicator(self, obj):
        return obj.short_registration_indicator()
    short_registration_indicator.short_description = "Registration Indicator"

@admin.register(SubnetSlot)
class SubnetSlotAdmin(admin.ModelAdmin):
    list_display = (
        "subnet",
        "blockchain",
        "netuid",
        "registered",
        "maximum_registration_price",
        "restart_threshold",
        "reinstall_threshold",
        "registration_block",
        "deregistration_block",
    )
    search_fields = ("subnet__name", "netuid")
    list_filter = ("blockchain",)

    def registered(self, obj):
        return obj.registered_status()

    def registration_block(self, obj):
        return obj.registration_block.serial_number if obj.registration_block else "N/A"

    registration_block.short_description = "Registration Block"

    def deregistration_block(self, obj):
        return obj.deregistration_block.serial_number if obj.deregistration_block else "N/A"

    deregistration_block.short_description = "Deregistration Block"


@admin.register(ValidatorInstance)
class ValidatorInstanceAdmin(admin.ModelAdmin):
    list_display = ("subnet_slot", "hotkey", "last_updated", "status", "server", "created_at")
    search_fields = ("hotkey", "subnet_slot__subnet__name", "server__name")


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("name", "ip_address", "validatorinstance", "description", "created_at")
    search_fields = ("name", "ip_address", "validator_instance__subnet_slot__subnet__name")

    def validatorinstance(self, obj):
        return obj.validator_instances.hotkey if obj.validator_instances else "N/A"


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "discord_id", "email")
    search_fields = ("name", "discord_id", "email")


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "timestamp")
    search_fields = ("serial_number",)


@admin.register(Hotkey)
class HotkeyAdmin(admin.ModelAdmin):
    list_display = ("hotkey", "is_mother")
    search_fields = ("hotkey",)
