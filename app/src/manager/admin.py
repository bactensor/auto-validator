from collections import OrderedDict
from typing import Any
from django.contrib import admin
from django.contrib import messages
from .models import Subnet, SubnetSlot, ValidatorInstance, Server, Operator, Block, Hotkey
from django.urls import path
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings


# Admin Classes
@admin.register(Subnet)
class SubnetAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'get_operator_count')
    search_fields = ('name',)
    list_filter = ('operators',)

    def get_operator_count(self, obj):
        return obj.operators.count()

    get_operator_count.short_description = 'Number of Operators'


@admin.register(SubnetSlot)
class SubnetSlotAdmin(admin.ModelAdmin):
    list_display = ('subnet', 'blockchain', 'netuid', 'restart_threshold', 'reinstall_threshold', 'get_registration_block', 'get_deregistration_block')
    search_fields = ('subnet__name', 'netuid')
    list_filter = ('blockchain',)

    def get_registration_block(self, obj):
        return obj.registration_block.serial_number if obj.registration_block else 'N/A'

    get_registration_block.short_description = 'Registration Block'

    def get_deregistration_block(self, obj):
        return obj.deregistration_block.serial_number if obj.deregistration_block else 'N/A'

    get_deregistration_block.short_description = 'Deregistration Block'

@admin.register(ValidatorInstance)
class ValidatorInstanceAdmin(admin.ModelAdmin):
    list_display = ('subnet_slot', 'hotkey', 'last_updated', 'status', 'server', 'created_at')
    search_fields = ('hotkey', 'subnet_slot__subnet__name', 'server__name')


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'description', 'created_at')
    search_fields = ('name', 'ip_address')

@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'discord_id', 'email')
    search_fields = ('name', 'discord_id', 'email')

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'timestamp')
    search_fields = ('serial_number',)

@admin.register(Hotkey)
class HotkeyAdmin(admin.ModelAdmin):
    list_display = ('hotkey','is_mother')
    search_fields = ('hotkey',)