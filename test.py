import yaml

config_path = "configs/stt_config.yaml"

with open(config_path, 'r') as f:
        config = yaml.safe_load(f)


print(config['datasets']['egyptian_asr'])



dataset_name = "egyptian_asr"

if dataset_name in config['datasets']: 
    print(True)