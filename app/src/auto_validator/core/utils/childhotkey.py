import logging
import sys
from io import StringIO

from bittensor import Wallet
from bittensor_cli import CLIManager

from ..models import Hotkey


class ChildHotkey:
    def __init__(
        self, parent_wallet_name: str, parent_hotkey_name: str, parent_wallet_path: str = "~/.bittensor/wallets"
    ):
        self.logger = logging.getLogger(__name__)
        self.parent_wallet_name = parent_wallet_name
        self.parent_hotkey_name = parent_hotkey_name
        self.parent_wallet_path = parent_wallet_path

    def connect_to_parent_wallet(self):
        self.parent_wallet = Wallet(name=self.parent_wallet_name, hotkey=self.parent_hotkey_name)
        if not self.parent_wallet.coldkey_file.exists_on_device():
            raise ValueError("Coldkey file for parent wallet %s not found.", self.parent_wallet_name)
        if not self.parent_wallet.hotkey_file.exists_on_device():
            raise ValueError("Hotkey file for parent wallet %s not found.", self.parent_wallet_name)

    def __enter__(self):
        self.connect_to_parent_wallet()
        return self

    def create_new_child_hotkey(
        self,
        network: str,
        netuid: int,
        child_wallet_name: str,
        child_hotkey_name: str,
        proportion: float = 1,
    ) -> str:
        child_wallet = Wallet(name=child_wallet_name, hotkey=child_hotkey_name)
        if not child_wallet.coldkey_file.exists_on_device():
            child_wallet.create_new_coldkey(overwrite=False, use_password=False)
        if not child_wallet.hotkey_file.exists_on_device():
            child_wallet.create_new_hotkey(overwrite=False, use_password=False)

        cli_manager = CLIManager()
        sys.stdin = StringIO("y\n")
        cli_manager.stake_set_children(
            wallet_name=self.parent_wallet_name,
            wallet_hotkey=self.parent_hotkey_name,
            wallet_path=self.parent_wallet_path,
            network=network,
            netuid=netuid,
            all_netuids=False,
            children=[child_wallet.hotkey.ss58_address],
            proportions=[proportion],
            quiet=True,
            verbose=False,
            wait_for_finalization=True,
            wait_for_inclusion=True,
        )
        sys.stdin = sys.__stdin__
        Hotkey.objects.create(hotkey=child_wallet.hotkey.ss58_address)
        return child_wallet.hotkey.ss58_address

    def get_child_hotkeys(self, network: str, netuid: int):
        cli_manager = CLIManager()
        result = cli_manager.stake_get_children(
            wallet_name=self.parent_wallet_name,
            wallet_hotkey=self.parent_hotkey_name,
            wallet_path=self.parent_wallet_path,
            network=network,
            netuid=netuid,
            all_netuids=False,
            quiet=True,
            verbose=False,
        )
        return result

    def revoke_child_hotkeys(
        self,
        network: str,
        netuid: int,
    ) -> bool:
        cli_manager = CLIManager()
        sys.stdin = StringIO("y\n")
        cli_manager.stake_revoke_children(
            wallet_name=self.parent_wallet_name,
            wallet_hotkey=self.parent_hotkey_name,
            wallet_path=self.parent_wallet_path,
            network=network,
            netuid=netuid,
            all_netuids=False,
            quiet=True,
            verbose=False,
            wait_for_finalization=True,
            wait_for_inclusion=True,
        )
        sys.stdin = sys.__stdin__
        return True
