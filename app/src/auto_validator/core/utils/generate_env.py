import json
import sys

def generate_env(pre_config_path, env_path, subnet_codename):
    with open(pre_config_path, 'r') as pre_config_file:
        pre_config = json.load(pre_config_file)
    
    with open(env_path, 'w') as env_file:
        for key, value in pre_config.items():
            env_file.write(f"{key}={value}\n")
        env_file.write(f"SUBNET_CODENAME={subnet_codename}\n")

if __name__ == "__main__":
    pre_config_path = sys.argv[1]
    env_path = sys.argv[2]
    subnet_codename = sys.argv[3]
    generate_env(pre_config_path, env_path, subnet_codename)