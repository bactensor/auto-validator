import logging
import os

import paramiko  # type: ignore
from scp import SCPClient, SCPException  # type: ignore


class SSH_Manager:
    def __init__(self, host: str, username: str, key_filename: str, passphrase: str, port: int = 22):
        self.host = host
        self.port = port
        self.username = username
        self.key_filename = key_filename
        self.passphrase = passphrase
        self.logger = logging.getLogger("console")

    def connect(self) -> bool:
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                key_filename=self.key_filename,
                passphrase=self.passphrase,
            )
        except Exception as e:
            self.logger.exception(f"SSH Execute Command Error: {e}")
            return False
        return True

    def execute_command(self, command: str) -> str:
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            stdout.channel.recv_exit_status()
            if stderr.read().decode("utf-8"):
                self.logger.error(f"Command: {command} failed with error: {stderr.read().decode('utf-8')}")
                return ""
            self.logger.info(f"Command: {command} executed successfully")
            return stdout.read().decode("utf-8")
        except Exception as e:
            self.logger.exception(f"SSH Execute Command Error: {e}")
            return ""

    def close(self):
        self.client.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def copy_files_to_remote(self, local_files: str, remote_path: str) -> None:
        # Check if the remote path exists, if not, create it
        if remote_path.endswith("/"):
            self.execute_command(f"mkdir -p {remote_path}")
        else:
            remote_dir = os.path.dirname(remote_path)
            self.execute_command(f"mkdir -p {remote_dir}")

        self.logger.info(f"{local_files} will be copied to {remote_path}")

        if self.client.get_transport() is None or not self.client.get_transport().is_active():
            raise Exception("SSH connection is not open")

        with SCPClient(self.client.get_transport()) as scp:
            try:
                for local_file in local_files:
                    scp.put(local_file, remote_path)
                    # If remote_path is a file, we only need to copy one file
                    if not remote_path.endswith("/"):
                        break
                self.logger.info("Files copied to remote server successfully")
            except SCPException as e:
                self.logger.exception(f"SCP Error: {e}")
            except OSError as e:
                self.logger.exception(f"IOError: {e}")
