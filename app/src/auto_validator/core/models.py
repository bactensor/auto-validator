from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import F, Q


def validate_hotkey_length(value):
    if len(value) != 48:
        raise ValidationError("Hotkey must be exactly 48 characters long.")


class UploadedFile(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    file_name = models.CharField(max_length=4095)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    storage_file_name = models.CharField(
        max_length=4095,
        db_comment="File name (id) in Django Storage",
    )
    file_size = models.PositiveBigIntegerField(db_comment="File size in bytes")

    def __str__(self):
        return f"{self.file_name!r} uploaded by {self.user}"

    @property
    def url(self):
        return default_storage.url(self.storage_file_name)


class Block(models.Model):
    serial_number = models.IntegerField(primary_key=True, unique=True)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.serial_number}"


class Subnet(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    operators = models.ManyToManyField("Operator", related_name="subnets", blank=True)

    def registered_networks(self):
        mainnet_slots = self.slots.filter(
            Q(
                Q(registration_block__isnull=False, deregistration_block__isnull=True)
                | Q(
                    registration_block__isnull=False,
                    deregistration_block__isnull=False,
                    registration_block__gt=F("deregistration_block"),
                )
            ),
            blockchain="mainnet",
        )
        testnet_slots = self.slots.filter(
            Q(
                Q(registration_block__isnull=False, deregistration_block__isnull=True)
                | Q(
                    registration_block__isnull=False,
                    deregistration_block__isnull=False,
                    registration_block__gt=F("deregistration_block"),
                )
            ),
            blockchain="testnet",
        )

        mainnet_indicator = f"sn{mainnet_slots.first().netuid}" if mainnet_slots.exists() else ""
        testnet_indicator = f"t{testnet_slots.first().netuid}" if testnet_slots.exists() else ""

        return f"{mainnet_indicator}{testnet_indicator}" or "-"

    def __str__(self):
        return self.name


class SubnetSlot(models.Model):
    subnet = models.ForeignKey(Subnet, on_delete=models.PROTECT, null=True, blank=True, related_name="slots")
    blockchain = models.CharField(max_length=50, choices=[("mainnet", "Mainnet"), ("testnet", "Testnet")])
    netuid = models.IntegerField()
    maximum_registration_price = models.IntegerField(default=0, help_text="Maximum registration price in RAO")
    registration_block = models.ForeignKey(
        "Block", on_delete=models.PROTECT, null=True, blank=True, related_name="registration_slots"
    )
    deregistration_block = models.ForeignKey(
        "Block", on_delete=models.PROTECT, null=True, blank=True, related_name="deregistration_slots"
    )
    restart_threshold = models.IntegerField(default=0)
    reinstall_threshold = models.IntegerField(default=0)

    def __str__(self):
        subnet_name = self.subnet.name if self.subnet else "No subnet"
        suffix = " (unregistered)" if self.registration_block and not self.registration_block else ""
        return f"{self.blockchain} / sn{self.netuid}: {subnet_name} {suffix}"


class Hotkey(models.Model):
    hotkey = models.CharField(max_length=48, validators=[validate_hotkey_length], unique=True)
    is_mother = models.BooleanField(default=False)

    def __str__(self):
        return self.hotkey


class ValidatorInstance(models.Model):
    subnet_slot = models.ForeignKey(SubnetSlot, on_delete=models.PROTECT, related_name="validator_instances")
    hotkey = models.ForeignKey(
        "Hotkey", on_delete=models.PROTECT, null=True, blank=True, related_name="validator_instances"
    )
    last_updated = models.PositiveIntegerField(null=True, blank=True)
    status = models.BooleanField(default=False)
    uses_child_hotkey = models.BooleanField(default=False)
    server = models.OneToOneField("Server", on_delete=models.PROTECT, related_name="validator_instances")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.hotkey)


class Operator(models.Model):
    name = models.CharField(max_length=255)
    discord_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Server(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    ssh_private_key = models.CharField(
        max_length=255, null=True, blank=True, help_text="Path to the SSH private key file"
    )
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip_address
