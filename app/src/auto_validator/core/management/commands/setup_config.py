import configparser
import os

from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv

load_dotenv()


class Command(BaseCommand):
    """
    Django management command to create or update a configuration file.
    This command generates a config.ini file based on the subnet codename
    and autovalidator address, storing the configuration in the CONFIG_DIR(env) directory.
    """

    help = "Create or update the configuration file."

    def add_arguments(self, parser):
        # Get codename from env variable.
        codename = os.getenv("CODENAME")
        if not codename:
            raise CommandError("CODENAME environment variable is not set.")

        # Get auto validator address from env variable.
        autovalidator_address = os.getenv("AUTOVALIDATOR_ADDRESS")
        if not codename:
            raise CommandError("AUTOVALIDATOR_ADDRESS environment variable is not set.")

        # This argument is optional to specify the subnet's codename and defaults to the CODENAME(env).
        parser.add_argument("-c", "--codename", type=str, help="The codename of the subnet", default=codename)

        # This argument is optional and defaults to the AUTOVALIDATOR_ADDRESS(env).
        parser.add_argument(
            "-a", "--autovalidator_address", type=str, help="The auto validator address", default=autovalidator_address
        )

    def handle(self, *args, **options):
        """
        Handle the command execution:
        - Fetch the command arguments (codename and autovalidator address).
        - Create the configuration directory if the directory doesn't exist.
        """
        codename = options["codename"]
        autovalidator_address = options["autovalidator_address"]

        # Get configuration directory from env variable.
        config_base_dir = os.getenv("CONFIG_DIR")

        # Check if the CONFIG_DIR environment variable is set
        if not config_base_dir:
            raise CommandError("CONFIG_DIR environment variable is not set.")

        config_expanded_dir = os.path.expanduser(config_base_dir)

        # Create the configuration directory if doesn't exists
        try:
            os.makedirs(config_expanded_dir, exist_ok=True)
        except Exception as e:
            raise CommandError(f"Failed to create configuration directory: {config_expanded_dir}.\n Error: {e}")

        # Define the full path for the configuration file
        config_path = os.path.join(config_expanded_dir, "config.ini")

        # Initialize a ConfigParser object
        config = configparser.ConfigParser()

        config["subnet"] = {"condename": codename, "autovalidator_address": autovalidator_address}

        # Write the configuration to config.ini
        try:
            with open(config_path, "w") as configfile:
                config.write(configfile)
        except Exception as e:
            raise CommandError(f"Failed to write to the configuration file: {config_path}.\n Error: {e}")

        # Output success message
        self.stdout.write(f"Configuration file created at {config_path}")
