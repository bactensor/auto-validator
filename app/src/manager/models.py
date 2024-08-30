from django.db import models


class Block(models.Model):
    serial_number = models.IntegerField(unique=True)  # Unique identifier for the block
    timestamp = models.DateTimeField()  # Time when the block was created

    def __str__(self):
        return f"Block {self.serial_number} at {self.timestamp}"

class Subnet(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)  # Additional field for description
    operators = models.ManyToManyField('Operator', related_name='subnets', blank=True)  # Link to operators

    def __str__(self):
        return self.name

class SubnetSlot(models.Model):
    subnet = models.ForeignKey(Subnet, on_delete=models.CASCADE, related_name='slots')
    blockchain = models.CharField(max_length=50, choices=[('mainnet', 'Mainnet'), ('testnet', 'Testnet')])
    netuid = models.IntegerField()  # Changed from id_on_chain to netuid
    registration_block = models.ForeignKey('Block', on_delete=models.SET_NULL, null=True, blank=True, related_name='registration_slots')
    deregistration_block = models.ForeignKey('Block', on_delete=models.SET_NULL, null=True, blank=True, related_name='deregistration_slots')
    restart_threshold = models.IntegerField(default=0)  # Threshold for restart
    reinstall_threshold = models.IntegerField(default=0)  # Threshold for reinstall

    def __str__(self):
        return f"{self.blockchain} / sn{self.netuid}: {self.subnet.name}"


class Hotkey(models.Model):
    hotkey = models.CharField(max_length=255)
    is_mother = models.BooleanField(default=False)
    def __str__(self):
        return self.hotkey

class ValidatorInstance(models.Model):
    subnet_slot = models.ForeignKey(SubnetSlot, on_delete=models.CASCADE, related_name='validator_instances')
    hotkey = models.ForeignKey('Hotkey', on_delete=models.SET_NULL, null=True, blank=True)
    last_updated = models.IntegerField(null=True, blank=True)
    status = models.BooleanField(default=False)
    # hotkey = models.ForeignKey('self', on_delete=models.CASCADE, related_name='child_instance', null=True, blank=True)
    uses_child_hotkey = models.BooleanField(default = False)
    server = models.OneToOneField('Server', on_delete=models.CASCADE, related_name='validator_instances')  # Link to Server
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.hotkey.__str__()
    


class Operator(models.Model):
    name = models.CharField(max_length=255)
    discord_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.name

class Server(models.Model):
    name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()  # Field for IP address
    ssh_private_key = models.CharField(max_length=255, null=True)  # Field for SSH key path (relative to ~/.auto-validator/ssh/)
    description = models.TextField(null=True, blank=True)  # Additional field for description
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip_address
