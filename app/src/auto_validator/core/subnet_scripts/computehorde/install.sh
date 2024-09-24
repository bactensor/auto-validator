#!/bin/bash
#no GPU

sudo apt update

cd ~/.bittensor/subtensor/
sudo docker-compose down

cd ~/.bittensor/subnets/compute_horde_validator/
sudo docker-compose down

# Rhef, action here --> we securely pull down this file with sshpass and sftp server: r-sn12-docker-compose.blob and overwrite: ~/.bittensor/subnets/compute_horde_validator/docker-compose.yml
# Rhef, action here --> we securely pull down this file with sshpass and sftp server: r-sn12-dotenv.env and overwrite: ~/.bittensor/subnets/compute_horde_validator/.env

sudo docker-compose up -d

echo "doing this: sudo docker-compose logs --follow validator-runner"
echo "doing this: sudo docker-compose logs --follow validator-runner"
echo "doing this: sudo docker-compose logs --follow validator-runner"

sudo docker-compose logs --follow validator-runner


