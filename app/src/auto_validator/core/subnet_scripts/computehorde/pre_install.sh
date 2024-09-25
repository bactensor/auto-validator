#!/bin/bash
#no GPU
#needs python 3.11

python --version
python3 --version
sudo apt update
sudo apt upgrade -y
#sudo add-apt-repository ppa:deadsnakes/ppa 
sudo apt install python3.11 -y
python3 --version
python3.11 --version
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 2
for i in {1..10}; do echo; echo "choose 2 for python 3.11  !!!!!!!!!"; echo; done
sudo update-alternatives --config python3
python3 --version
sudo apt install python-is-python3 -y
python --version

for i in {1..10}; do echo; echo "now try sudo apt update, and if error, do stuff in link or sudo apt remove python3-apt then sudo apt install python3-apt and then try sudo apt update again, maybe a reboot in between!!!!!!!!!!"; echo; done

# possible fix for 
# https://stackoverflow.com/questions/56218562/how-to-fix-modulenotfounderror-no-module-named-apt-pkg

mkdir ~/.bittensor/subnets/computehorde/
cd ~/.bittensor/subnets/computehorde/ || exit

#cloud
#export PYTHONPATH="${PYTHONPATH}:/root/.bittensor/subnets/scraping_subnet/"


