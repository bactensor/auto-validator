import json
import sys


def generate_env(env_template_path, pre_config_path, env_path):
    with open(env_template_path) as env_template_file:
        env_template = env_template_file.read()
    with open(pre_config_path) as pre_config_file:
        pre_config = json.load(pre_config_file)

    with open(env_path, "w") as env_file:
        env_file.write(f"{env_template}\n")
        for key, value in pre_config.items():
            env_file.write(f"{key}={value}\n")


if __name__ == "__main__":
    env_template_path = sys.argv[1]
    pre_config_path = sys.argv[2]
    env_path = sys.argv[3]
    generate_env(env_template_path, pre_config_path, env_path)
