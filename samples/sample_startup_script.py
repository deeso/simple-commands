from simple_commands import boto
from simple_commands import ssh
import json
import os


def build_setup_run_instance(instance_name, config, command_string_parameters=None):
    #initialize the boto command
    boto.Commands.set_config(**config)
    instances, volume_results = boto.Commands.build_instance_region('us-east-2', instance_name, config, max_count=1)
    instance_public_ip = boto.Commands.get_instance_public_ips([i for i in instances], **config)

    key_filename = list(instances.values())[0]['KeyName']
    # use the config to set up the hosts
    instances_configs = {i['name']: i for i in config.get('instance_descriptions', [])}
    instance_config = instances_configs.get(instance_name)
    keypath = config.get('ssh_key_path', '')
    key_file = os.path.join(keypath, key_filename)

    all_activities = config.get('activities')
    instance_actions = instances_configs.get('activities')

    # variables for passwords and such
    # variables for passwords and such
    command_string_parameters = instance_config.get('command_string_parameters', []) if command_string_parameters is None \
                                else command_string_parameters
    cmd_format_args = {i['name']: i['value'] for i in command_string_parameters}

    # iterate over the actions and then execut them.
    for action in instance_actions:
        activity = all_activities.get(action)
        atype = activity.get('type')
        if atype == 'commands':
            # create the command list
            commands = [i.format(**cmd_format_args) for i in activity.get('commands', [])]
            # TODO execute the commands
            for instance_id, host in instance_public_ip.items():
                ssh.Commands.execute_commands(commands, host=host, key_filename=key_file)        
        elif atype == 'upload_files':
            dst_src = {}
            for scp_args in activity.get('files', []):
                src = scp_args.get('src')
                dst = scp_args.get('dst')
                dst_src[dst] = src
            # scp the files over
            for instance_id, host in instance_public_ip.items():
                ssh.Commands.upload_files(dst_src, host=host, key_filename=key_file)
    return instance_public_ip

def build_setup_run_instance_multi_regions_count(instance_name, config, regions, max_count, command_string_parameters=None):
    #initialize the boto command
    boto.Commands.set_config(**config)
    all_instances = {}
    all_volumes = {}
    instance_id_key = {}
    keypath = config.get('ssh_key_path', '')
    for region in regions:
        instances, volumes = boto.Commands.build_instance_region('us-east-2', instance_name, config, max_count=1)
        all_volumes.update(volumes)
        all_instances.update(instances)
        key_filename = {k: os.path.join(keypath, v['KeyName']) for k,v in instances.items()}
        instance_id_key.update(key_filename)


    instance_public_ip = boto.Commands.get_instance_public_ips([i for i in instances], **config)
    # use the config to set up the hosts
    instances_configs = {i['name']: i for i in config.get('instance_descriptions', [])}
    instance_config = instances_configs.get(instance_name)
    

    all_activities = config.get('activities')
    instance_actions = instances_configs.get('activities')

    # variables for passwords and such
    command_string_parameters = instance_config.get('command_string_parameters', []) if command_string_parameters is None \
                                else command_string_parameters

    cmd_format_args = {i['name']: i['value'] for i in command_string_parameters}

    # iterate over the actions and then execut them.
    for action in instance_actions:
        activity = all_activities.get(action)
        atype = activity.get('type')
        if atype == 'commands':
            # create the command list
            commands = [i.format(**cmd_format_args) for i in activity.get('commands', [])]
            # TODO execute the commands
            for instance_id, host in instance_public_ip.items():
                key_file = instance_id_key[instance_id]
                ssh.Commands.execute_commands(commands, host=host, key_filename=key_file)        
        elif atype == 'upload_files':
            dst_src = {}
            for scp_args in activity.get('files', []):
                src = scp_args.get('src')
                dst = scp_args.get('dst')
                dst_src[dst] = src
            # scp the files over
            for instance_id, host in instance_public_ip.items():
                ssh.Commands.upload_files(dst_src, host=host, key_filename=key_file


# load configuration from json
config = json.load(open('samples/boto.json'))
instances_configs = {i['name']: i for i in config.get('instance_descriptions', [])}
instance_config = instances_configs.get(instance_name)

# initialize the mongodb instance
instance_name = "dockerhp-mongodb"
command_string_parameters = instances_configs[instance_name].get('command_string_parameters', []) if command_string_parameters is None \
                            else command_string_parameters
instance_public_ip = build_setup_run_instance(instance_name, config)
mongo_ip = list(instance_public_ip.values())[0]

# initialize the mongodb instance
# TODO update mongo ip and passwords in sample config file, upload them to collector instance
# TODO update tokens in the collector config from the sample boto config
instance_name = "dockerhp-collector"
_command_string_parameters = command_string_parameters
command_string_parameters = instances_configs[instance_name].get('command_string_parameters', []) if command_string_parameters is None \
                            else command_string_parameters

_command_string_parameters.update(command_string_parameters)
command_string_parameters = _command_string_parameters
# TODO take ip address from mongo and update the config for collector
instance_public_ip = build_setup_run_instance(instance_name, config, command_string_parameters=command_string_parameters)
collector_ip = list(instance_public_ip.values())[0]
command_string_parameters['collector_ip'] = collector_ip


# TODO update ip and passwords in sample config file, upload them to collector instance
# TODO update tokens in the collector config from the sample boto config
# TODO 
instance_name = "dockerhp"
_command_string_parameters = command_string_parameters
command_string_parameters = instances_configs[instance_name].get('command_string_parameters', []) if command_string_parameters is None \
                            else command_string_parameters

_command_string_parameters.update(command_string_parameters)
command_string_parameters = _command_string_parameters
# initialize the mongodb instance
build_setup_run_instance_multi_regions_count(instance_name, config, command_string_parameters=command_string_parameters)



