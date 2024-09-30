import csv
import difflib
import json
import os

import paramiko
import requests
import yaml
from django.conf import settings
from django.shortcuts import redirect, render
from scp import SCPClient

from ..models import Subnet

GITHUB_URL = settings.SUBNETS_INFO_GITHUB_URL
LOCAL_SUBNETS_SCRIPTS_PATH = settings.LOCAL_SUBNETS_SCRIPTS_PATH


def fetch_and_compare_subnets(request):
    response = requests.get(GITHUB_URL, timeout=30)
    if response.status_code != 200:
        return render(request, "admin/sync_error.html", {"error": "Failed to fetch data from GitHub."})

    github_data = response.json()
    db_data = list(Subnet.objects.values())

    github_data = [subnet for subnet in github_data.values()]
    db_data = [{k: v for k, v in subnet.items() if k != "id"} for subnet in db_data]
    github_data_str = json.dumps(github_data, indent=2, sort_keys=True)
    db_data_str = json.dumps(db_data, indent=2, sort_keys=True)

    diff = difflib.unified_diff(
        db_data_str.splitlines(), github_data_str.splitlines(), fromfile="db_data", tofile="github_data", lineterm=""
    )
    diff_str = "\n".join(diff)

    if request.method == "POST":
        new_data = list(github_data)
        for subnet_data in new_data:
            subnet, created = Subnet.objects.update_or_create(
                codename=subnet_data.get("codename"), defaults=subnet_data
            )
        return redirect("admin:core_subnet_changelist")

    return render(
        request,
        "admin/sync_subnets.html",
        {
            "diff_str": diff_str,
            "github_data": json.dumps(github_data),
        },
    )


def get_user_ip(request):
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip_address:
        ip_address = ip_address.split(",")[0]
    else:
        ip_address = request.META.get("REMOTE_ADDR")
    return ip_address


def create_ssh_client(ssh_ip_address, ssh_user, ssh_key_path, ssh_passphrase):
    """
    Create an SSH client.

    Args:
        ssh_ip_address (str): SSH IP address.
        ssh_user (str): SSH username.
        ssh_key_path (str): SSH key path.
        ssh_passphrase (str): SSH passphrase.
    Examples:
        create_ssh_client("123.41.223.12", "root", "/root/.ssh/id_rsa", "passphrase")
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ssh_ip_address, username=ssh_user, key_filename=ssh_key_path, passphrase=ssh_passphrase)
    return ssh


def copy_files_to_remote(ssh, local_files, remote_path):
    """
    Copy files to a remote server.

    Args:
        ssh: SSH client.
        local_files (list): List of local files to copy.
        remote_path (str): Remote path to copy the files.
    Examples:
        copy_files_to_remote(ssh, ["/root/.bittensor/wallets/validator/hotkeys/validator-hotkey"], "~/.bittensor/wallets/validator/hotkeys/")
    """
    # Check if the remote path exists, if not, create it
    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_path}")
    stdout.channel.recv_exit_status()  # Wait for the command to complete

    with SCPClient(ssh.get_transport()) as scp:
        for local_file in local_files:
            scp.put(local_file, remote_path)


def generate_env_file_on_remote(
    ssh, remote_generator_path, remote_env_template_path, remote_pre_config_path, remote_env_path
):
    """
    Generate .env file on a remote server.

    Args:
        ssh: SSH client.
        remote_generator_path (str): Remote path to the generator script.
        remote_env_template_path (str): Remote path to the .env.template file.
        remote_pre_config_path (str): Remote path to the pre_config.json file.
        remote_env_path (str): Remote path to the .env file.
    Examples:
        generate_env_file_on_remote(ssh, "/root/scripts/", "/root/scripts/.env.template", "/root/scripts/pre_config.json", "/root/scripts/.env")
    """
    command = f"python3 {os.path.join(remote_generator_path, 'generate_env.py')} {remote_env_template_path} {remote_pre_config_path} {remote_env_path}"
    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.read().decode())
    print(stderr.read().decode())


def generate_pre_config_file(subnet_codename: str, blockchain, netuid, yaml_file_path: str, csv_file_path: str):
    """
    Generate pre_config.json file from the YAML file and CSV file.

    Args:
        subnet_codename (str): Subnet codename
        yaml_file_path (str): Path to the YAML file
        csv_file_path (str): Path to the CSV file

    Examples:
        generate_pre_config_file("subnet1", "mainnet", "1", "subnets.yaml", "secrets.csv")
    """
    yaml_file_path = os.path.abspath(yaml_file_path)
    csv_file_path = os.path.abspath(csv_file_path)
    pre_config_path = os.path.abspath(f"{LOCAL_SUBNETS_SCRIPTS_PATH}/{subnet_codename}/pre_config.json")
    with open(yaml_file_path) as file:
        data = yaml.safe_load(file)
    if subnet_codename not in data:
        raise ValueError(f"Subnet codename {subnet_codename} not found in YAML file.")
    allowed_secrets = data[subnet_codename].get("allowed_secrets", [])

    secrets = {}
    with open(csv_file_path) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["SECRET_KEYS"] in allowed_secrets:
                secrets[row["SECRET_KEYS"]] = row["SECRET_VALUES"]
    secrets["SUBNET_CODENAME"] = subnet_codename
    secrets["BITTENSOR_NETWORK"] = "finney" if blockchain == "mainnet" else "test"
    secrets["BITTENSOR_NETUID"] = netuid

    with open(pre_config_path, "w") as file:
        json.dump(secrets, file, indent=4)

    return pre_config_path


def generate_dumper_commands(subnet_codename, yaml_file_path, dumper_commands_file_path):
    """
    Generate dumper commands from the YAML file and write them to a file.

    Args:
        subnet_codename (str): Subnet codename.
        yaml_file_path (str): Path to the YAML file.
        dumper_commands_file_path (str): Path to the file to write the dumper commands.

    Raises:
        ValueError: If subnet_codename is not found in the YAML file.

    Examples:
        generate_dumper_commands("subnet1", "subnets.yaml", "dumper_commands.sh")
    """
    yaml_file_path = os.path.abspath(yaml_file_path)
    with open(yaml_file_path) as file:
        data = yaml.safe_load(file)
    if subnet_codename not in data:
        raise ValueError(f"Subnet codename {subnet_codename} not found in YAML file.")
    commands = data[subnet_codename].get("dumper_commands", [])
    with open(dumper_commands_file_path, "w") as file:
        for command in commands:
            file.write(f"{command}\n")


def install_validator_on_remote_server(
    subnet_codename, blockchain, netuid, ssh_ip_address, ssh_user, ssh_key_path, ssh_passphrase
):
    """
    Install a validator on a remote server.

    Args:
        subnet_codename (str): Subnet codename.
        blockchain (str): Blockchain name.
        netuid (str): NetUID.
        ssh_ip_address (str): SSH IP address.
        ssh_user (str): SSH username.
        ssh_key_path (str): SSH key path.
        ssh_passphrase (str): SSH passphrase.

    Examples:
        install_validator_on_remote_server(
            "subnet1", "mainnet", "1", "123.41.223.2", "root", "/root/.ssh/id_rsa", "passphrase"
        )
    """
    ssh = create_ssh_client(ssh_ip_address, ssh_user, ssh_key_path, ssh_passphrase)

    yaml_file_path = f"{LOCAL_SUBNETS_SCRIPTS_PATH}/subnets.yaml"
    csv_file_path = f"{LOCAL_SUBNETS_SCRIPTS_PATH}/secrets.csv"

    local_hotkey_path = "/root/.bittensor/wallets/validator/hotkeys/validator-hotkey"
    local_coldkeypub_path = "/root/.bittensor/wallets/validator/coldkeypub.txt"

    generate_pre_config_file(subnet_codename, blockchain, netuid, yaml_file_path, csv_file_path)

    dumper_commands_file_path = f"{LOCAL_SUBNETS_SCRIPTS_PATH}/{subnet_codename}/dumper_commands.sh"
    generate_dumper_commands(subnet_codename, yaml_file_path, dumper_commands_file_path)

    # Extract remote path from .env.template file
    local_env_template_path = f"{LOCAL_SUBNETS_SCRIPTS_PATH}/{subnet_codename}/.env.template"

    with open(local_env_template_path) as env_file:
        for line in env_file:
            if line.startswith("TARGET_PATH"):
                remote_path = line.split("=")[1].strip()
                break
    local_directory = f"{LOCAL_SUBNETS_SCRIPTS_PATH}/{subnet_codename}/"
    local_files = [
        os.path.join(local_directory, file)
        for file in os.listdir(local_directory)
        if os.path.isfile(os.path.join(local_directory, file))
    ]
    local_generator_path = f"{LOCAL_SUBNETS_SCRIPTS_PATH}/generate_env.py"
    local_files.append(local_generator_path)
    copy_files_to_remote(ssh, local_files, remote_path)

    remote_hotkey_path = "~/.bittensor/wallets/validator/hotkeys/"
    local_hotkey_file = [local_hotkey_path]
    copy_files_to_remote(ssh, local_hotkey_file, remote_hotkey_path)

    remote_coldkey_path = "~/.bittensor/wallets/validator/"
    local_coldkey_file = [local_coldkeypub_path]
    copy_files_to_remote(ssh, local_coldkey_file, remote_coldkey_path)

    generate_env_file_on_remote(
        ssh, remote_path, f"{remote_path}/.env.template", f"{remote_path}/pre_config.json", f"{remote_path}/.env"
    )

    # Run pre_install.sh on remote server
    stdin, stdout, stderr = ssh.exec_command(f"bash {remote_path}/install.sh")
    print(stdout.read().decode())
    print(stderr.read().decode())

    # Run install.sh on remote server
    stdin, stdout, stderr = ssh.exec_command(f"bash {remote_path}/install.sh")
    print(stdout.read().decode())
    print(stderr.read().decode())

    ssh.close()
