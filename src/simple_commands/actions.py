from .consts import *
from .util import *
from . import boto
from . import ssh
import traceback
import json
import os

import logging
ACTION_LOGGER = get_stream_logger(__name__)

command_strings_to_dict = lambda x: {i['name']: i['value'] for i in x}

def perform_activity(instance_name, all_instances, activity_name, 
                     instance_public_ip, boto_config, command_format_args, username=UBUNTU):
    # get instance config
    instances_configs = {i['name']: i for i in boto_config.get('instance_descriptions', [])}
    instance_config = instances_configs.get(instance_name)
    
    # get activities and actions for setup sequence
    instance_activities = instance_config.get('activities')
    activity = instance_activities.get(activity_name)
    all_actions = boto_config.get("actions")
    keypath = boto_config.get('ssh_key_path', '')

    ssh_reqs = {} 
    for iid, iinfo in all_instances.items():
        key_filename = list(all_instances.values())[0]['KeyName']
        key_file = os.path.join(keypath, key_filename)
        ssh_reqs[iid] = {'key_file': key_file, 'host': instance_public_ip[iid], 'username': username}
    ACTION_LOGGER.info("Performing {} for {} ({} instances)".format(activity_name, instance_name, len(all_instances)))
    return perform_instance_activities(instance_name, all_instances, activity_name,  activity, 
                                       all_actions, ssh_reqs, command_format_args, boto_config)


def perform_instance_activities(instance_name:str, all_instances:dict, activity_name:str, 
                                activity: dict, all_actions:dict, ssh_reqs: dict,
                                command_format_args, boto_config):
    # iterate over the actions and then execut them.
    steps = activity.get('steps')
    activity_results = {'instance_name':instance_name,
                        'activity_name': activity_name, 
                        "step_results": [], 
                        "steps": steps,
                        "command_format_args": command_format_args}
    
    unpack_ssh_reqs = lambda reqs: (reqs['host'], reqs['key_file'], reqs['username']) 
    for action in steps:
        activity = all_actions.get(action)
        atype = activity.get('type')
        pre_wait = activity.get('pre_wait', 0.0)
        time.sleep(pre_wait)
        if atype == 'commands':
            # create the command list
            commands = [i.format(**command_format_args) for i in activity.get('commands', [])]
            aresults = {'name': action,
                        'type':'commands', 
                        "commands": commands, "results":[], 
                        }
            # TODO execute the commands
            for instance_id, ssh_req in ssh_reqs.items():
                host, key_file, username = unpack_ssh_reqs(ssh_req)
                ACTION_LOGGER.debug("Performing {}:{} ({} elements) for {}@{} with {}".format(activity_name, atype, len(commands), username, host, key_file))
                result = ssh.Commands.execute_commands(commands, host=host, key_filename=key_file, username=username)
                outcome = {'instance_id': instance_id, "host": host, 'result': result}
                aresults["results"].append(outcome)
        elif atype == 'upload_files':
            dst_src = {}    
            for scp_args in activity.get('files', []):
                src = scp_args.get('src')
                dst = scp_args.get('dst')
                dst_src[dst] = src
            aresults = {'name': action,
                        'atype':atype, 
                        "dst_src_files": dst_src, 
                        "results":[]}
            # scp the files over
            for instance_id, ssh_req in ssh_reqs.items():
                ACTION_LOGGER.debug("Performing {}:{} ({} elements) for {}@{} with {}".format(activity_name, atype, len(dst_src), username, host, key_file))
                host, key_file, username = unpack_ssh_reqs(ssh_req)
                result = ssh.Commands.upload_files(dst_src, host=host, key_filename=key_file, username=username)
                outcome = {'instance_id': instance_id, "host": host, 'result': result}
                aresults["results"].append(outcome)
            activity_results['step_results'][action] = aresults
        elif atype == "boto":
            aresults = {'name': action,
                        'atype':atype,
                        "commands": activity.get('commands', []),
                        "command_parameters": activity.get('command_parameters', []),
                        "results":[]}
            # scp the files over
            for instance_id, ssh_req in ssh_reqs.items():
                host, key_file, username = unpack_ssh_reqs(ssh_req)
                ACTION_LOGGER.debug("Invalid activity {}:{} for {}@{} with {}".format(activity_name, atype, username, host, key_file))
                outcome = {'instance_id': instance_id, "host": host, 'result': "Unsupported action"}
                aresults["results"].append(outcome)
            activity_results['step_results'].append(aresults)
        else:
            aresults = {'name': action,
                        'atype':atype,  
                        "results":[]}
            for instance_id, ssh_req in ssh_reqs.items():
                host, key_file, username = unpack_ssh_reqs(ssh_req)
                ACTION_LOGGER.debug("Invalid activity {}:{} for {}@{} with {}".format(activity_name, atype, username, host, key_file))
                outcome = {'instance_id': instance_id, "host": host, 'result': "Unsupported action"}
                aresults["results"].append(outcome)
            activity_results['step_results'].append(aresults)
        post_wait = activity.get('post_wait', 0.0)
        time.sleep(post_wait)            
    return activity_results


def build_instance_and_setup(instance_name, config, setup_activity_name="setup", command_format_args: dict=None, region=None, max_count=None):
    #initialize the boto command
    ACTION_LOGGER.debug("Initializing the boto.Commands klass".format())
    boto.Commands.set_config(**config)

    # get instance config
    instances_configs = {i['name']: i for i in config.get('instance_descriptions', [])}
    instance_config = instances_configs.get(instance_name)
    
    # prep format arguments for env
    command_string_parameters = instance_config.get('command_string_parameters', [])
    command_format_args = command_format_args if command_format_args else {}
    command_format_args.update(command_strings_to_dict(command_string_parameters))

    # get activities and actions for setup sequence
    instance_activities = instances_configs.get('activities')
    all_actions = config.get('actions')
    
    
    # ssh key stuff
    username = instance_config.get('username', UBUNTU)
    keypath = config.get('ssh_key_path', '')
    
    # use the config to set up the hosts
    ACTION_LOGGER.info("Creating {} instances in {} for '{}'".format(max_count, region, instance_name))
    all_instances, all_volumes = boto.Commands.build_instance_region(region, instance_name, config, max_count=max_count)
    ACTION_LOGGER.info("Created {} instances and {} volumes for '{}' in {}".format(len(all_instances), len(all_volumes), instance_name, region))
    instance_public_ip = boto.Commands.get_instance_public_ips([i for i in all_instances], **config)
    
    # create path to ssh key
    key_filename = list(all_instances.values())[0]['KeyName']
    key_file = os.path.join(keypath, key_filename)
    
    # perform setup activity
    setup_results = None
    ACTION_LOGGER.info("Setting-up {} instances and {} volumes for '{}' in {} with activity: '{}'".format(len(all_instances), len(all_volumes), instance_name, region, setup_activity_name))
    try:
        setup_results = perform_activity(instance_name, all_instances, setup_activity_name, instance_public_ip, config, command_format_args)
    except:
        ACTION_LOGGER.info("Failed setup: {} ".format(traceback.format_exc()))
    return all_instances, instance_public_ip, all_volumes, setup_results

def build_instance_and_setup_multi_regions_count(instance_name, config, regions, max_count, command_format_args=None, setup_activity_name="setup"):
    #initialize the boto command
    boto.Commands.set_config(**config)
    all_instances = {}
    all_volumes = {}
    instance_id_key = {}
    keypath = config.get('ssh_key_path', '')
    backup_config = config.copy()
    
    all_instances = {}
    instance_public_ip = {}
    all_volumes = {}
    setup_results = {}

    for region in regions:
        ai, ipi, av, sr = boto.Commands.build_instance_and_setup(instance_name, config, setup_activity_name=setup_activity_name, 
                                                                 command_format_args=command_format_args, region=region, 
                                                                 max_count=max_count)
        
        all_instances[region] = ai
        instance_public_ip[region] = ipi
        all_volumes[region] = av
        setup_results[region] = sr

    return all_instances, instance_public_ip, all_volumes, setup_results
