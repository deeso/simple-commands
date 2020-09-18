from simple_commands.consts import *
from simple_commands import boto
from simple_commands import ssh
from simple_commands.actions import *
import json
import os


def handle_collector_config_update_and_start(instance_name, base_collector_config: str, collector_instances: dict, 
                                             instance_public_ip: dict, command_format_args: dict, boto_config: dict):

    base_collector_config = json.load(open('collector_config_sample.json'))
    collector_config = base_collector_config.copy()
    for k, v in command_format_args.items()
        if k in collector_config:
            collector_config[k] = v

    alt_collector_config = base_collector_config.copy()
    for k, v in command_format_args.items():
        if k in alt_collector_config:
            alt_collector_config[k] = v

    collector_host = command_format_args.get('collector_host')
    alt_collector_host = command_format_args.get('alt_collector_host')
    collector_token = command_format_args.get('collector_token')

    # primary collector
    collector_config['global_hostname'] = collector_host
    collector_config['collector_host'] = collector_host
    collector_config['collector_alt_host'] = collector_alt_host
    collector_config["collector_token"] = collector_token
    collector_config["server_secret_key"] = collector_token

    # alternate collector
    alt_collector_config['global_hostname'] = collector_alt_host
    alt_collector_config['collector_host'] = collector_alt_host
    alt_collector_config['collector_alt_host'] = collector_ip
    alt_collector_config["collector_token"] = collector_token
    alt_collector_config["server_secret_key"] = collector_token

    ssh.Commands.upload_bytes(collector_config, "collector_config.json", host=host, key_filename=key_filename)
    ssh.Commands.upload_bytes(alt_collector_config, "collector_config.json", host=host, key_filename=key_filename)
    activity_name = "startup", 
    return perform_activity(instance_name, collector_instances, activity_name, instance_public_ip, boto_config, command_format_args)

def handle_honeypot_config_update_and_start(instance_name, base_honeypot_config: str, collector_instances: dict, 
                                             instance_public_ip: dict, command_format_args: dict, boto_config: dict):

    base_collector_config = json.load(open('collector_config_sample.json'))
    collector_config = base_collector_config.copy()
    for k, v in command_format_args.items()
        if k in collector_config:
            collector_config[k] = v

    alt_collector_config = base_collector_config.copy()
    for k, v in command_format_args.items():
        if k in alt_collector_config:
            alt_collector_config[k] = v

    collector_host = command_format_args.get('collector_host')
    alt_collector_host = command_format_args.get('alt_collector_host')
    collector_token = command_format_args.get('collector_token')

    ssh.Commands.upload_bytes(collector_config, "collector_config.json", host=host, key_filename=key_filename)
    ssh.Commands.upload_bytes(alt_collector_config, "collector_config.json", host=host, key_filename=key_filename)
    activity_name = "startup", 
    return perform_activity(instance_name, collector_instances, activity_name, instance_public_ip, boto_config, command_format_args)


# load configuration from json
boto_config = json.load(open('internal-scripts/boto.json'))
instances_configs = {i['name']: i for i in boto_config.get('instance_descriptions', [])}
boto.Commands.set_config(**boto_config)

# initialize the mongodb instance
instance_name = "dockerhp-mongodb"
instance_config = instances_configs.get(instance_name)
command_string_parameters = instances_configs['dockerhp-mongodb'].get('command_string_parameters', [])
mdb_command_format_args = command_strings_to_dict(command_string_parameters)

# all_instances, instance_public_ip, all_volumes, setup_results = build_instance_and_setup
mdb_ai, mdb_ipi, mdb_av, mdb_sr = build_instance_and_setup(instance_name, boto_config, command_format_args=mdb_command_format_args)
mongo_host = list(mdb_ipi.values())[0]
mongo_password = mdb_command_format_args['mongo_pass']

# initialize the collector instance
instance_name = "dockerhp-collector"
command_string_parameters = instances_configs[instance_name].get('command_string_parameters', [])
dc_command_format_args = command_strings_to_dict(command_string_parameters)

base_collector_config = "collector_config_sample.json"
dc_ai, dc_ipi, dc_av, dc_sr = build_instance_and_setup(instance_name, boto_config, command_format_args=dc_command_format_args)

collector_host = None
alt_collector_host = None
if len(dc_ipi) > 1:
    collector_host, alt_collector_host = [ip for ip in dc_ipi.values()][:2]
else:
    collector_host = [ip for ip in dc_ipi.values()][0]
    alt_collector_host = collector_host

command_format_args['collector_host'] = collector_host
command_format_args['alt_collector_host'] = alt_collector_host
command_format_args['mongo_host'] = mongo_host
command_format_args['mongo_password'] = mongo_host
handle_collector_config_update_and_start(instance_name, base_collector_config, dc_ai, dc_ipi, dc_command_format_args, boto_config)




instance_name = "dockerhp"
dhp_cmd_args = command_strings_to_dict(instances_configs[instance_name].get('command_string_parameters', []))
_command_string_parameters.update(command_string_parameters)
command_string_parameters = _command_string_parameters
# initialize the mongodb instance
dhp_all_instances, dhp_instance_public_ip, dhp_all_volumes = build_instance_and_setup_multi_regions_count(instance_name, boto_config, command_string_parameters=dc_command_string_parameters)

# handle the configuration update
collector_config = json.load(open('collector_config_sample.json'))









