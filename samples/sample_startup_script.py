from simple_commands import boto
from simple_commands import ssh
import json
import os
# load configuration from json
config = json.load(open('samples/boto.json'))
#initialize the boto command
boto.Commands.set_config(**config)

# initialize the mongodb instance
instance_name = "dockerhp-mongodb"
instances, volume_results = boto.Commands.build_instance_region('us-east-2', instance_name, config, max_count=1)
instance_public_ip = boto.Commands.get_instance_public_ips([i for i in instances], **config)

key_filename = list(instances.values())[0]['KeyName']
# use the config to set up the hosts
instances_configs = {i['name']: i for i in config.get('instance_descriptions', [])}
instance_config = instances_configs.get(instance_name)
keypath = config.get('ssh_key_path', '')
key_file = os.path.join(keypath, key_filename)

# variables for passwords and such
command_string_parameters = instance_config.get('command_string_parameters', [])
format_args = {i['name']: i['value'] for i in command_string_parameters}

# create the command list
commands = [i.format(**format_args) for i in instance_config.get('setup_commands', [])]
# TODO execute the commands
for instance_id, host in instance_public_ip.items():
    ssh.Commands.execute_commands(commands, host=host, key_filename=key_file)

# enumerate files for upload
dst_src = {}
for scp_args in instance_config.get('upload_files', []):
    src = scp_args.get('src')
    dst = scp_args.get('dst')
    dst_src[dst] = src

# scp the files over
for instance_id, host in instance_public_ip.items():
    ssh.Commands.upload_files(dst_src, host=host, key_filename=key_file)

# use ssh client to start the final commands
final_commands = ["docker-compose up -d collector_mongo", ]
for instance_id, host in instance_public_ip.items():
    ssh.Commands.execute_commands(commands, host=host, key_filename=key_file)

