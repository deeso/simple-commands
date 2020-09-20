import os
import boto3
from .consts import *
from .util import *
import traceback
import time

class Commands(object):
    AWS_SECRET_ACCESS_KEY = None
    AWS_ACCESS_KEY_ID = None
    DEFAULT_REGION='us-east-2'
    DEFAULT_KMS_ID = None
    DEFAULT_KMS_ALIAS = None
    DEFAULT_KMS_ARN = None
    REGIONS = [DEFAULT_REGION]
    LOGGER = get_stream_logger(__name__ + '.Commands')

    @classmethod
    def get_image_id(cls, instance_name, region, boto_config):
        instance_description = cls.get_instance_description(instance_name, boto_config)
        ami_id = instance_description.get('ami_id', None)
        ami_region = instance_description.get('ami_region', None)
        if ami_id and ami_region and ami_region == region:
            return ami_id
        region_to_ami = boto_config.get('region_to_ami', {})
        if region in region_to_ami:
            return region_to_ami[region]
        return None

    @classmethod
    def get_instance_type(cls, instance_name, boto_config):
        instance_description = cls.get_instance_description(instance_name, boto_config)
        if 'instance_type' in instance_description:
            return instance_description['instance_type']
        return boto_config.get('instance_type', 't2.micro')

    @classmethod
    def get_instance_key_info(cls, instance_name, config, **kargs):
        instance_config = cls.get_instance_description(instance_name, config)
        base_keyname = instance_config.get('base_keyname', 'aws-instance-key')
        keyname_fmt = instance_config.get('keyname_fmt', "{base_keyname}.pem")
        _kargs = kargs.copy()
        _kargs['base_keyname'] = base_keyname
        key_info = {
            'key_path': config.get('ssh_key_path', './ssh_keys/'),
            'key_name': keyname_fmt.format(**_kargs),
            'recreate': config.get('recreate', False)   
        }
        return key_info

    @classmethod
    def create_tag_specs(cls, resource_type,  tags, tag_config_type='key_value'):
        tag_spec = None
        if tag_config_type == 'raw':
            tag_spec = tags
        elif tag_config_type == 'key_value':
            tag_spec = {'ResourceType': resource_type,
                        'Tags': [{'Key':k, 'Value': v} for k, v in tags.items()]
                        }
        return tag_spec

    @classmethod
    def get_tag_specs_configs(cls, boto_config, tag_specs=None, tag_specs_names=None, resource_type='instance'):
        if tag_specs is None:
            tag_specs = boto_config.get('tag_specs', [])
        if tag_specs_names and len(tag_specs_names) > 0:
            tag_specs = [i for i in tag_specs if i['name'] in tag_specs_names]
        
        tag_specifications = []
        for tag_config in tag_specs:
            rtype = tag_config.get('resource_type', resource_type)
            if rtype != resource_type:
                continue
            tags = tag_config.get('tags', {})
            tag_config_type = tag_config.get('tag_config_type', 'key_value')
            if rtype:
                tag_specifications.append(cls.create_tag_specs(rtype, tags, tag_config_type))
        return tag_specifications

    @classmethod
    def get_instance_description(cls, instance_name, boto_config):
        configs = boto_config.get('instance_descriptions', [])
        for config in configs:
            x = config.get('name', None)
            if x and x == instance_name:
                return config
        return {}

    @classmethod
    def get_instance_names(cls, boto_config):
        configs = boto_config.get('instance_descriptions', [])
        names = []
        for config in configs:
            x = config.get('name', None)
            if x:
                names.append(x)
        return names

    @classmethod
    def get_instance_descriptions(cls, boto_config):
        configs = boto_config.get('instance_descriptions', [])
        iconfigs = {}
        for config in configs:
            x = config.get('name', None)
            if x:
                iconfigs[x] = config
        return iconfigs

    @classmethod
    def get_instance_config_elements(cls, instance_name, element, boto_config):
        description = cls.get_instance_description(instance_name, boto_config)
        if description is None:
            return None
        citems = boto_config.get(element, [])
        configs = []
        instance_items = description.get(element, [])
        for item in citems:
            if 'name' in item and item['name'] in instance_items:
                configs.append(item)
        return configs

    @classmethod
    def get_volume_tags_configs(cls, volume_name, boto_config):
        tag_spec_names = boto_config.get('volumes', {}).get(volume_name, {}).get('tag_specs', None)
        if tag_specs_names:
            return cls.get_tag_specs_configs(config, tag_specs_names=tag_spec_names, resource_type='volume')
        return None

    @classmethod
    def get_volume_description(cls, volume_name, boto_config):
        volume_configs = boto_config.get('volumes', [])
        if len(volume_configs) == 0:
            return None
        vcs = cls.get_volume_descriptions(boto_config)
        return vcs.get(volume_name, None)

    @classmethod
    def get_volume_descriptions(cls, boto_config):
        volume_configs = boto_config.get('volumes', [])
        if len(volume_configs) == 0:
            return None
        return {config.get('name'): config for config in volume_configs if 'name'}

    @classmethod
    def get_volume_device_descriptions(cls, instance_name, volume_names, boto_config):
        volume_names = [] if not isinstance(volume_names, list) else volume_names
        instance_config = cls.get_instance_description(instance_name, boto_config)
        device_configs = instance_config.get('volume_devices', [])
        return device_configs

    @classmethod
    def get_instance_security_group_configs(cls, instance_name, boto_config):
        return cls.get_instance_config_elements(instance_name, 'security_groups', boto_config)

    @classmethod
    def get_instance_tag_specifications(cls, instance_name, boto_config):
        instance_config = cls.get_instance_description(instance_name, boto_config)
        
        tag_specs_names = instance_config.get('tag_specs', None)
        if tag_specs_names:
            return cls.get_tag_specs_configs(boto_config, tag_specs_names=tag_specs_names, resource_type='instance')
        return None


    @classmethod
    def get_instance_volumes_configs(cls, instance_name, boto_config):
        return cls.get_instance_config_elements(instance_name, 'volumes', boto_config)

    @classmethod
    def get_instance_security_group(cls, instance_name, boto_config):
        description = cls.get_instance_description(instance_name, boto_config)
        if description is None:
            return None
        sgs = boto_config.get('security_groups', [])
        sg_config = []
        instance_sgs = description.get('security_groups', [])
        for sg in sgs:
            if 'name' in sg and sg['name'] in instance_sgs:
                sg_config.append(sg)
        return sg

    @classmethod
    def set_config(cls, **kargs):
        cls.AWS_ACCESS_KEY_ID = kargs.get('aws_access_key_id', None)
        cls.AWS_SECRET_ACCESS_KEY= kargs.get('aws_secret_access_key', None)
        cls.REGIONS = kargs.get('regions', cls.REGIONS) 
        cls.DEFAULT_KMS_ID = kargs.get('aws_key_id', None)
        cls.DEFAULT_KMS_ALIAS = kargs.get('aws_key_alias', None)
        cls.init_kms_defaults(**kargs)

    @classmethod
    def create_tags_keywords(cls, *extra_args):
        tags = {}
        for k,v in zip(extra_args[::2],extra_args[1::2]):        
            key = None
            if k.startswith(TAG_MARKER):
                key = k[len(TAG_MARKER):]
            else:
                continue
            key = key.replace('-','_')
            tags[key] = v
        return tags

    @classmethod
    def get_ec2(cls, ec2=None, region=DEFAULT_REGION, aws_secret_access_key=None, aws_access_key_id=None, **kargs):
        if ec2 is None:
            # cls.LOGGER.debug("Creating ec2 client for {} in {}".format(region, aws_access_key_id))
            aws_secret_access_key = aws_secret_access_key if aws_secret_access_key else cls.AWS_SECRET_ACCESS_KEY
            aws_access_key_id = aws_access_key_id if aws_access_key_id else cls.AWS_ACCESS_KEY_ID
            ec2 = boto3.client('ec2', 
                           region, 
                           aws_access_key_id=aws_access_key_id, 
                           aws_secret_access_key=aws_secret_access_key)
        return ec2

    @classmethod
    def get_kws_key(cls, kms=None, region=DEFAULT_REGION, aws_secret_access_key=None, aws_access_key_id=None,
                    key_name=None, key_id=None, **kargs):

        if key_name is None and key_id is None:
            if cls.DEFAULT_KMS_ID:
                return cls.DEFAULT_KMS_ID

            kms = cls.get_kms(region=region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        return kms

    @classmethod
    def init_kms_defaults(cls, **kargs):
        kms = cls.get_kms(**kargs)
        aliases = kms.list_aliases()
        rsp = kms.list_keys()
        all_keys = {k['KeyId']: k['KeyArn'] for k in rsp['Keys']}
        alias_name = cls.DEFAULT_KMS_ALIAS if cls.DEFAULT_KMS_ALIAS else 'alias/aws/ebs'
        alias_key_id = cls.DEFAULT_KMS_ID
        if alias_key_id is not None and alias_name is not None:
            return kms.describe_key(KeyId=cls.DEFAULT_KMS_ID)
        if cls.DEFAULT_KMS_ID:
            cls.DEFAULT_KMS_ALIAS = "None"
            for alias in aliases['Aliases']:
                if 'TargetKeyId' in alias and alias['TargetKeyId'] == alias_key_id:
                    cls.DEFAULT_KMS_ID = alias['TargetKeyId']
                    cls.DEFAULT_KMS_ALIAS = alias['AliasName']
                    break
        else:
            for alias in aliases['Aliases']:
                if alias['AliasName'] == alias_name:
                    cls.DEFAULT_KMS_ID = alias['TargetKeyId']
                    cls.DEFAULT_KMS_ALIAS = alias['AliasName']
                    break
        if cls.DEFAULT_KMS_ID is None:
            cls.DEFAULT_KMS_ID = list(all_keys.keys())[0]
            cls.DEFAULT_KMS_ALIAS = "None"
            cls.DEFAULT_KMS_ARN = all_keys[cls.DEFAULT_KMS_ID]
        else:
            cls.DEFAULT_KMS_ARN = all_keys[cls.DEFAULT_KMS_ID]

    @classmethod
    def get_default_kms_key(cls, **kargs):
        if cls.DEFAULT_KMS_ID is None:
            cls.init_kms_defaults(**karg)
        return {'alias':cls.DEFAULT_KMS_ALIAS, 
                'keyarn':cls.DEFAULT_KMS_ARN, 
                'keyid':cls.DEFAULT_KMS_ID}

    @classmethod
    def check_kms_key(cls, key_arn=None, key_id=None, **kargs):
        cls.LOGGER.debug("checking key: arn={}, id={}".format(key_arn, key_id))
        info = cls.get_kms_key(key_arn=key_arn, key_id=key_id, **kargs)
        return not info is None

    @classmethod
    def create_kms_key(cls, tags=None, **kargs):
        kms = cls.get_kms(**kargs)
        cls.LOGGER.info("creating a new kms key".format(key_arn, key_id))
        # TODO add tags
        _kargs = {}
        if tags:
            _kargs['Tags'] = tags

        x = kms.create_key(**tags)
        y = x['KeyMetadata']
        return {'alias':"None", 
                'keyarn':y['Arn'], 
                'keyid':y['KeyId']}

    @classmethod
    def get_kms_key(cls, key_arn=None, key_id=None, create=False, **kargs):
        cls.LOGGER.info("geting a kms key: arn={}, id={} create={}".format(key_arn, key_id, create))
        if key_arn is None and key_id is None and create:
            return cls.create_kms_key(**kargs)
        if key_id and cls.DEFAULT_KMS_ID and cls.DEFAULT_KMS_ID == key_id or \
           key_arn and cls.DEFAULT_KMS_ARN and cls.DEFAULT_KMS_ARN == key_arn:
            return cls.get_default_kms_key(**kargs)
        if key_id is None and key_arn is None:
            return cls.get_default_kms_key(**kargs)
        kms = cls.get_kms(**kargs)
        aliases = kms.list_aliases()
        rsp = kms.kms.list_keys()
        setit = False
        if key_id:
            all_keys = {k['KeyId']: k['KeyArn'] for k in rsp['Keys']}
            key_arn = all_keys.get(key_id, None)
            setit = key_id in all_keys
        else:
            all_keys = {k['KeyArn']:k['KeyId'] for k in rsp['Keys']}
            key_id = all_keys.get(key_arn, None)
            setit = key_arn in all_keys
        
        if setit:
            return {'alias':"None", 
                    'keyarn':key_arn, 
                    'keyid':key_id}
        elif create:
            return cls.create_key(**kargs)
        cls.LOGGER.info("Failed to get a kms key: arn={}, id={} create={}".format(key_arn, key_id, create))
        return None

    @classmethod
    def get_default_aws_key_id(cls, **kargs):
        kms = cls.get_kms(region=region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        aliases = kms.list_aliases()

        alias_name = cls.DEFAULT_KMS_ALIAS if cls.DEFAULT_KMS_ALIAS else 'alias/aws/ebs'
        alias_key_id = cls.DEFAULT_KMS_ID
        if alias_key_id is not None and alias_name is not None:
            return kms.describe_key(KeyId=cls.DEFAULT_KMS_ID)
        if cls.DEFAULT_KMS_ID:
            for alias in aliases['Aliases']:
                if 'TargetKeyId' in alias and alias['TargetKeyId'] == alias_key_id:
                    cls.DEFAULT_KMS_ID = alias['TargetKeyId']
                    cls.DEFAULT_KMS_ALIAS = alias['AliasName']
                    break
        else:
            for alias in aliases['Aliases']:
                if alias['AliasName'] == alias_name:
                    cls.DEFAULT_KMS_ID = alias['TargetKeyId']
                    cls.DEFAULT_KMS_ALIAS = alias['AliasName']
                    break
        if cls.DEFAULT_KMS_ID:
            return kms.describe_key(KeyId=cls.DEFAULT_KMS_ID)
        return None

    @classmethod
    def get_kms(cls, kms=None, region=DEFAULT_REGION, aws_secret_access_key=None, aws_access_key_id=None, **kargs):
        if kms is None:
            cls.LOGGER.debug("Creating ec2 client for {} in {}".format(region, aws_access_key_id))
            aws_secret_access_key = aws_secret_access_key if aws_secret_access_key else cls.AWS_SECRET_ACCESS_KEY
            aws_access_key_id = aws_access_key_id if aws_access_key_id else cls.AWS_ACCESS_KEY_ID
            kms = boto3.client('kms', 
                           region, 
                           aws_access_key_id=aws_access_key_id, 
                           aws_secret_access_key=aws_secret_access_key)
        return kms

    @classmethod
    def delete_key_pair(cls, keyname, **kargs):
        ec2 = cls.get_ec2(**kargs)
        try:
            cls.LOGGER.info("Deleting keypair: {}".format(keyname))
            ec2.delete_key_pair(KeyName=keyname)
        except:
            raise

    @classmethod
    def get_key_pair(cls, key_name, key_path, recreate=False, **kargs):
        ec2 = cls.get_ec2(**kargs)
        key_filename = os.path.join(key_path, key_name)
        try:
            ec2.describe_key_pairs(KeyNames=[key_name])
            if os.path.exists(key_path) and not recreate:
                return key_filename
            elif recreate:
                cls.delete_key_pair(keyname=key_name, ec2=ec2)
        except:
            pass

        try:
            os.remove(key_filename)
            cls.LOGGER.info("Deleted key file from disk: {}".format(key_filename))
        except:
            pass

        cls.LOGGER.info("Creating keypair: {}".format(key_name))
        key_pair = ec2.create_key_pair(KeyName=key_name)
        cls.LOGGER.info("Writing key file to disk: {}".format(key_filename))
        outfile = open(key_filename,'w')
        KeyPairOut = str(key_pair['KeyMaterial'])
        outfile.write(KeyPairOut)
        outfile.close()
        os.chmod(key_filename, 0o600)
        return key_filename

    @classmethod
    def delete_security_group(cls, sg_name=None, sg_id=None, **kargs):
        ec2 = cls.get_ec2(**kargs)
        _kargs = {}
        if sg_id:
            cls.LOGGER.info("Deleting Security Group ID: {}".format(sg_id))
            _kargs['GroupId'] = sg_name
        elif sg_name:
            cls.LOGGER.info("Deleting Security Group: {}".format(sg_name))
            _kargs['GroupName'] = sg_name
        else:
            return False
        try:
            rsp = ec2.delete_security_group(**_kargs)
            cls.LOGGER.info("Deleted Security Group".format())
            return True
        except:
            pass
        return False

    @classmethod
    def create_security_group(cls, sg_name, sg_description, ingress, refresh=False, **kargs):
        ec2 = cls.get_ec2(**kargs)
        try:
            rsp = ec2.describe_security_groups(GroupNames=[sg_name])
            sg_id = rsp['SecurityGroups'][0]['GroupId']
            if not refresh:
                return rsp['SecurityGroups'][0]['GroupId']
            cls.delete_security_group(sg_name=sg_name, sg_id=sg_id, ec2=ec2, **kargs)
        except:
            pass

        cls.LOGGER.info("Creating Security Group: {}".format(sg_name))
        rsp = ec2.create_security_group(GroupName=sg_name,
                                             Description=sg_description)
        sg_id = rsp.get('GroupId', None)
        if sg_id is None:
            raise Exception("Unable to create the security group")
        cls.LOGGER.info("Updating Security Group {} ingress rules".format(sg_id))
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=ingress)
        return sg_id

    @classmethod
    def create_instances(cls, key_name, max_count, image_id, instance_type, security_groups, 
                         tag_specifications, availability_zone, do_hibernate=False, device_name='/dev/sda1', 
                         delete_on_termination=True, volume_size=20, volumetype='gp2', encrypted=False,
                         kms_key_id=None, kms_arn_id=None, create_volume=True, snapshotid=None, **kargs):
        
        ec2 = cls.get_ec2(**kargs)
        placement = None

        if availability_zone is not None:
            placement = {'AvailabilityZone': availability_zone}
        
        _kargs = {}
        block_info = None
        ebs = {
            'Encrypted': encrypted
        }
        if do_hibernate and any([instance_type.find(it) == 0 for i in HIBERNATEABLE]):
            _kargs['HibernationOptions'] = {'Configured': True}
            ebs['Encrypted'] = True

        if create_volume:
            ebs.update({
                'DeleteOnTermination': delete_on_termination,
                'VolumeSize': volume_size,
                'VolumeType': volumetype,
            })
            block_info = { 
                'DeviceName': device_name,
                'Ebs': ebs 
            }
            if ebs['Encrypted']:
                info = cls.get_kms_key(kms_key_id=kms_key_id, key_arn=kms_key_arn, create=True, tags=tags, **kargs)
                keyid = None
                if info is None:
                    keyid = info['keyid']
                ebs.update({
                    'KmsKeyId': keyid
                })
            if ebs['Encrypted'] and ebs['KmsKeyId'] is None:
                cls.LOGGER.critical("No valid key used for the encrypted volume")
                raise Exception("No valid key used for the encrypted volume")

            if snapshotid:
                ebs['SnapshotId'] = snapshotid
                del ebs['VolumeSize']
            _kargs['BlockDeviceMappings'] = [block_info,]

        _kargs.update({
            "DryRun":False, 
            "MinCount":1, 
            "MaxCount":max_count, 
            "ImageId":image_id, 
            "KeyName":key_name, 
            "InstanceType":instance_type, 
            "SecurityGroupIds":security_groups, 
            "TagSpecifications":tag_specifications,
            "Placement":placement,
        })
        
        del_keys = [i for i,v  in _kargs.items() if v is None ]
        for k in del_keys:
            del _kargs[k]

        cls.LOGGER.info("Starting {} '{}' instances in with {} ".format(max_count, instance_type, key_name))
        reservations = ec2.run_instances(**_kargs) 

        instances = [i['InstanceId'] for i in reservations['Instances']]
        if len(instances) > 0:
            r = ec2.describe_instances(InstanceIds=instances)
            instance_infos = []
            for k in r['Reservations']:
                instance_infos = instance_infos + k['Instances']
            t = {k['InstanceId']: k for k in instance_infos }
            return t
        return None

    @classmethod
    def create_security_groups(cls, security_group_configs, boto_config):
        sg_ids = []
        for sg in security_group_configs:
            sg_name = sg.get("name", None)
            sg_description = sg.get("description", None)
            ingress = sg.get("permissions", None)
            refresh = sg.get('refresh', False)
            sg_id = cls.create_security_group(sg_name, sg_description, ingress, 
                                              refresh=refresh, **boto_config)
            if sg_id:
                sg_ids.append(sg_id)
        return sg_ids

    @classmethod
    def wait_for_instances(cls, instance_ids, **kargs):
        ec2 = cls.get_ec2(**kargs)
        loaded_instances = None
        cls.LOGGER.info("Waiting for {} instances to be reachable".format(len(instance_ids)))
        while True:
            loaded_instances = cls.check_for_instances_up(instance_ids)
            if len(loaded_instances) == 0:
                time.sleep(5.0)
            elif len(loaded_instances) == len(instance_ids):
                break
            else:
                time.sleep(10.0)
        cls.LOGGER.info("{} instances are available".format(len(instance_ids)))
        return cls.get_instances(instance_ids=[i for i in loaded_instances])

    @classmethod
    def wait_for_volumes(cls, volume_ids, **kargs):
        ec2 = cls.get_ec2(**kargs)
        statuses = None
        cls.LOGGER.info("Waiting for {} volumes to be available".format(len(volume_ids)))
        while True:
            if len(volume_ids) == 0:
                break
            # print(instance_ids)
            rsp = ec2.describe_volumes(VolumeIds=volume_ids)
            # print(rsp)
            statuses = {i['VolumeId']: i for i in rsp['Volumes']}
            if len(statuses) == 0:
                time.sleep(5.0)
            elif all([i['State'] == 'available' for i in statuses.values()]):
                break
            else:
                time.sleep(10.0)
        cls.LOGGER.info("{} volumes are available".format(len(volume_ids)))
        return statuses

    @classmethod
    def build_instance_region(cls, region, instance_name, boto_config, max_count=None):
        region = region if region else cls.DEFAULT_REGION
        instance_config = cls.get_instance_description(instance_name, boto_config)
        if len(instance_config) == 0:
            raise Exception("Incomplete instance configurations")
        max_count = max_count if max_count else instance_config.get('max_count', 1)

        cls.LOGGER.info("Creatinng {} instances for '{}' in {}".format(max_count, instance_name, region))
        instance_sg_configs = cls.get_instance_security_group_configs(instance_name, boto_config)
        instance_volume_configs = cls.get_instance_volumes_configs(instance_name, boto_config)

        instance_tag_specifigations = cls.get_instance_tag_specifications(instance_name, boto_config)

        # create keys
        key_info = cls.get_instance_key_info(instance_name, boto_config, region=region)
        key_name = key_info.get("key_name", None)
        key_filename = cls.get_key_pair(key_info['key_name'], key_info['key_path'], 
                                        recreate=key_info['recreate'], **boto_config)
        # create security groups
        security_groups = cls.create_security_groups(instance_sg_configs, boto_config)

        # create instance
        max_count = max_count if max_count else instance_config.get('max_count', 1)
        image_id = cls.get_image_id(instance_name, region, boto_config)
        instance_type = cls.get_instance_type(instance_name, boto_config)

        global_availability_zone =  boto_config.get('availability_zone', None)
        local_availability_zone  = instance_config.get('availability_zone', None)
        availability_zone = local_availability_zone if local_availability_zone else global_availability_zone 

        omit_kargs = boto_config.copy()
        if 'security_groups' in omit_kargs:
            del omit_kargs['security_groups']
        if 'instance_type' in omit_kargs:
            del omit_kargs['instance_type']

        if "availability_zone" in omit_kargs:
            del omit_kargs["availability_zone"]

        
        instance_infos = cls.create_instances(key_name, max_count, image_id, instance_type, security_groups, 
                         instance_tag_specifigations, availability_zone, **omit_kargs)
        
        if instance_infos is None:
            raise Exception("Failed to create instance: {}".format(instance_name))
        # create volumes in same zone
        instance_ids = list(instance_infos.keys())
        instance_statuses = cls.wait_for_instances(instance_ids)
        volume_names = instance_config.get('volumes', [])
        volume_results = None
        if len(volume_names) > 0:
            # create the volume
            cls.LOGGER.info("Creating {} volumes for '{}' in {}".format(len(volume_names), instance_name, region))
            volume_results = cls.attach_instances_to_volumes(instance_name, instance_statuses, volume_names, boto_config)
        return instance_infos, volume_results

    @classmethod
    def attach_instances_to_volumes(cls, instance_name, instance_statuses, volume_names, boto_config):
        volume_configs = cls.get_volume_descriptions(boto_config)
        device_configs = {k['volume']: k for k in cls.get_volume_device_descriptions(instance_name, volume_names, boto_config)}
        volume_results = {}
        for name in volume_names:
            volume_config = volume_configs.get(name, None)
            device_config = device_configs.get(name, {})
            volume_results[name] = {}
            if volume_config is None or len(volume_config) == 0 or \
               device_config is None or len(device_config) == 0:
                raise Exception("Attempting to create a volume ({}) for {}, but the device or volume configs are missing",format(name, instance_name)) 
            
            device_name = device_config['device']
            size = volume_config.get('size', None)
            availability_zone = volume_config.get('availability_zone', None)
            snapshotid = volume_config.get('snapshotid', None)
            volumetype = volume_config.get('volumetype', 'standard')
            multiattach = volume_config.get('multiattachenabled', False)
            encrypted = volume_config.get('encrypted', False)
            tags = volume_config.get('tag_specs', [])
            tag_specifications = cls.get_tag_specs_configs(boto_config, tag_specs_names=tags, resource_type='volume')
            size = volume_config.get('size', 100)
            vids = []
            for instance_id, instance_info in instance_statuses.items():
                availability_zone = instance_info.get('AvailabilityZone')
                vid = cls.create_volume(availability_zone=availability_zone, snapshotid=snapshotid, 
                                  volumetype=volumetype,  multiattach=multiattach,  encrypted=encrypted,
                                  tags=tag_specifications,  size=size, **boto_config)
                
                volume_results[name][instance_id] = {'volume_id': vid,
                                                     'volume_name': name,
                                                     'instance_name': instance_name,
                                                     'device': device_name,
                                                     'attached': False,
                                                     'response': None}
                # use this to capture arguments and attach each volume once they
                # are all available
                vids.append([vid, (instance_id, vid, device_name)])
            
            # wait for all the volumes to be available before attaching them
            _ = cls.wait_for_volumes([i[0] for i in vids], **boto_config)
            for vid, args in vids:
                if vid:
                    rsp = cls.attach_volume(*args, **boto_config)
                    volume_results[name][instance_id]['response'] = rsp
                    volume_results[name][instance_id]['attached'] = True
        return volume_results


    @classmethod
    def get_availability_zones(cls, **kargs):
        ec2 = cls.get_ec2(**kargs)
        zones = ec2.describe_availability_zones()['AvailabilityZones']
        az = [z['ZoneName'] for z in zones if z['State'].lower() == 'available']
        return az

    @classmethod
    def attach_volume(cls, instance_id, volume_id, device_name, **kargs):
        ec2 = cls.get_ec2(**kargs)
        cls.LOGGER.info("Attaching volume ({}) to '{}' as {}".format(instance_id, volume_id, device_name))
        rsp = ec2.attach_volume(InstanceId=instance_id, VolumeId=volume_id, Device=device_name)
        return rsp

    @classmethod
    def create_volume(cls, availability_zone=None, snapshotid=None, volumetype="gp2", multiattach=False,
                      encrypted=False, tags=None, size=None, **kargs):
        ec2 = cls.get_ec2(**kargs)

        if availability_zone is None:
            # grab the first one
            az = cls.get_availability_zones(ec2=ec2)
            if len(az) == 0:
                raise Exception("Unable to get an AvailabilityZone")
            availability_zone = az[0]
        _kargs = {"AvailabilityZone": availability_zone,
                  "VolumeType": volumetype, "MultiAttachEnabled": multiattach,
                  "Encrypted": encrypted}
        if tags:
            _kargs["TagSpecifications"] = tags
        if snapshotid:
            _kargs["SnapshotId"] = snapshotid
        if size:
            _kargs["Size"] = size
        # print(_kargs)
        if snapshotid:
            cls.LOGGER.info("Creating volume ({}:{}) using {} in {}".format(volumetype, size, snapshotid, availability_zone, ))
        else:    
            cls.LOGGER.info("Creating volume ({}:{}) in {} for".format(volumetype, size, availability_zone))

        rsp = ec2.create_volume(**_kargs)
        # print(rsp)
        if 'VolumeId' in rsp:
            return rsp['VolumeId']
        return None

    @classmethod
    def check_for_instances_up(cls, instances, **kargs):
        ec2 = cls.get_ec2(**kargs)
        instances_completed_loading = []
        statuses = ec2.describe_instance_status(InstanceIds=instances)
        for status in statuses['InstanceStatuses']:
            instance_id = status['InstanceId']
            if status['InstanceState']['Code'] != 16:
                continue
            if status['InstanceStatus']['Status'] != 'ok':
                continue
            if status['SystemStatus']['Status'] != 'ok':
                continue

            instances_completed_loading.append(instance_id)
        return instances_completed_loading

    @classmethod
    def extract_public_ips(cls, instance_infos):
        instance_to_ip = {k['InstanceId']: k.get('PublicIpAddress', '') for k in instance_infos}
        return instance_to_ip

    @classmethod
    def get_instance_public_ips(cls, instance_ids, **kargs):
        ec2 = cls.get_ec2(**kargs)
        results = ec2.describe_instances(InstanceIds=instance_ids)
        instance_infos = []
        for k in results['Reservations']:
            instance_infos = instance_infos + k['Instances']
        return cls.extract_public_ips(instance_infos)

    @classmethod
    def find_relevant_instances(cls, target_tags: dict=None, **kargs):
        target_tags = target_tags if target_tags else {}
        relevant_instances = {}
        ec2 = cls.get_ec2(**kargs)
        rsp = ec2.describe_instances()
        reservations = rsp.get('Reservations', {})
        for reservation in reservations:
            instances = reservation.get('Instances', [])
            for instance in instances:
                tags = instance.get('Tags', None)
                instance_id = instance['InstanceId']
                public_ip = instance.get('PublicIpAddress', '')
                if tags is None:
                    continue

                d_tags = {tag.get('Key', ''):tag.get('Value', '') for tag in tags }
                matching = {k:v for k, v in target_tags.items() if k in d_tags and v == d_tags[k]}
                if len(matching) == len(target_tags):
                    matching['public_ip'] = public_ip
                    relevant_instances[instance_id] = matching
        return relevant_instances

    @classmethod
    def find_relevant_volumes(cls, target_tags: dict=None, **kargs):
        target_tags = target_tags if target_tags else {}
        relevant_volumes = {}
        ec2 = cls.get_ec2(**kargs)
        rsp = ec2.describe_volumes()
        volumes = rsp.get('Volumes', {})
        for vinfo in volumes:
            tags = vinfo.get('Tags', None)
            volume_id = vinfo['VolumeId']
            if tags is None:
                continue
            d_tags = {tag.get('Key', ''):tag.get('Value', '') for tag in tags }
            matching = {k:v for k, v in target_tags.items() if k in d_tags and v == d_tags[k]}
            if len(matching) == len(target_tags):
                relevant_volumes[volume_id] = matching
        return relevant_volumes

    @classmethod
    def get_instances(cls, instance_id=None, instance_ids=None, target_tags=None, **kargs):
        ec2 = cls.get_ec2(**kargs)
        if instance_ids is None:
            instance_ids = []

        if instance_id not in instance_ids:
            instance_ids.append(instance_id)

        instances = {}
        if len(instance_ids) == 0:
            r = ec2.describe_instances(InstanceIds=instances)
            instance_infos = []
            for k in r['Reservations']:
                instance_infos = instance_infos + k['Instances']
            instances = {k['InstanceId']: k for k in instance_infos }
        if target_tags:
            if not 'ec2' in kargs:
                kargs['ec2'] = ec2
            x = find_relevant_instances(target_tags=target_tags, **kargs)
            if len(x) > 0:
                r = ec2.describe_instances(InstanceIds=[i for i in x])
                instance_infos = []
                for k in r['Reservations']:
                    instance_infos = instance_infos + k['Instances']
                instances.update({k['InstanceId']: k for k in instance_infos })
        return instances



    @classmethod
    def find_relevant_instances_multiple_regions(cls, target_tags: dict=None, regions=REGIONS, **kargs):
        target_tags = target_tags if target_tags else {}
        relevant_instances = []
        for region in regions:
            kargs['region'] = region
            instances = cls.find_relevant_instances(target_tags=target_tags, **kargs)
            relevant_instances.append({'region': region, 'instances': instances})
        return relevant_instances

    @classmethod
    def find_relevant_volumes_multiple_regions(cls, target_tags: dict=None, regions=REGIONS, **kargs):
        target_tags = target_tags if target_tags else {}
        relevant_instances = []
        for region in regions:
            kargs['region'] = region
            volumes = cls.find_relevant_volumes(target_tags=target_tags, **kargs)
            relevant_instances.append({'region': region, 'volumes': volumes})
        return relevant_instances

    @classmethod
    def terminate_relevant_instances(cls, instance_ids=None, instance_id=None, target_tags: dict=None, dry_run=True, **kargs):
        if instance_ids is None:
            instance_ids = []

        if instance_id not in instance_ids:
            instance_ids.append(instance_id)

        if len(instance_ids) == 0 and (target_tags is None or len(target_tags) == 0):
            cls.LOGGER.critical("WARNING: Must provide tags to filter out instances, or this will destroy the environment")
            raise Exception("Must provide tags to filter out instances, or this will destroy the environment")


        instances = cls.get_instances(instance_ids=instance_id, target_tags=target_tags, **kargs)
        if len(instances) == 0 and len(instance_ids) == 0:
            return instances

        ec2 = cls.get_ec2(**kargs)
        instance_ids = [i for i in instances]
        try:
            cls.LOGGER.debug("Attempting to terminate {} instances.".format(len(instance_ids)))
            ec2.terminate_instances(DryRun=dry_run, InstanceIds=instance_ids)
            cls.LOGGER.info("Terminated {} instances.".format(len(instance_ids)))
        except KeyboardInterrupt:
            cls.LOGGER.error("Failed to terminate {} instances.".format(len(instance_ids)))
        except:
            cls.LOGGER.error("{}".format(traceback.format_exc()))

        return instances

    @classmethod
    def delete_relevant_volumes(cls, target_tags: dict=None, dry_run=True, **kargs):
        if target_tags is None or len(target_tags) == 0:
            cls.LOGGER.critical("WARNING: Must provide tags to filter out instances, or this will destroy the environment")
            raise Exception("Must provide tags to filter out instances, or this will destroy the environment")

        volumes = cls.find_relevant_volumes(target_tags=target_tags, **kargs)
        if len(volumes) == 0:
            cls.LOGGER.info("No volumes found.")
            return volumes

        ec2 = cls.get_ec2(**kargs)
        for vid in volumes:
            try:
                cls.LOGGER.debug("Attempting to delete volume: {}.".format(vid))
                ec2.delete_volume(DryRun=dry_run, VolumeId=vid)
                cls.LOGGER.info("Deleted volume: {}.".format(vid))
            except KeyboardInterrupt:
                break
            except:
                cls.LOGGER.error("Failed to delete volume: {}.".format(vid))
                cls.LOGGER.error("{}".format(traceback.format_exc()))

        return volumes

    @classmethod
    def terminate_relevant_instances_multiple_regions(cls, regions=REGIONS, dry_run=True, **kargs):
        relevant_instances = []
        for region in regions:
            kargs['region'] = region
            results = cls.terminate_relevant_instances(dry_run=dry_run, **kargs)
            relevant_instances.append({'region': region, 'instances': results})
        return relevant_instances

    @classmethod
    def delete_relevant_volumes_multiple_regions(cls, regions=REGIONS, dry_run=True, **kargs):
        relevant_volumes = []
        for region in regions:
            kargs['region'] = region
            results = cls.delete_relevant_volumes(dry_run=dry_run, **kargs)
            relevant_volumes.append({'region': region, 'volumes': results})
        return relevant_volumes

    @classmethod
    def stop_relevant_instances(cls, instance_ids=None, instance_id=None, target_tags: dict=None, dry_run=True, **kargs):
        if instance_ids is None:
            instance_ids = []

        if instance_id not in instance_ids:
            instance_ids.append(instance_id)

        if len(instance_ids) == 0 and (target_tags is None or len(target_tags) == 0):
            cls.LOGGER.critical("WARNING: Must provide tags to filter out instances, or this will destroy the environment")
            raise Exception("Must provide tags to filter out instances, or this will destroy the environment")


        instances = cls.get_instances(instance_ids=instance_id, target_tags=target_tags, **kargs)
        if len(instances) == 0 and len(instance_ids) == 0:
            return instances

        ec2 = cls.get_ec2(**kargs)
        instance_ids = [i for i in instances]
        try:
            cls.LOGGER.debug("Attempting to stop {} instances: {}.".format(len(instance_ids)))
            ec2.stop_instances(DryRun=dry_run, InstanceIds=instance_ids)
            cls.LOGGER.info("Stopped instace: {}.".format(vid))
        except KeyboardInterrupt:
            cls.LOGGER.error("Failed to stop {} instances.".format(len(instance_ids)))
        except:
            cls.LOGGER.error("{}".format(traceback.format_exc()))

        return instances

    @classmethod
    def reboot_relevant_instances(cls, instance_ids=None, instance_id=None, target_tags: dict=None, dry_run=True, **kargs):
        if instance_ids is None:
            instance_ids = []

        if instance_id not in instance_ids:
            instance_ids.append(instance_id)

        if len(instance_ids) == 0 and (target_tags is None or len(target_tags) == 0):
            cls.LOGGER.critical("WARNING: Must provide tags to filter out instances, or this will destroy the environment")
            raise Exception("Must provide tags to filter out instances, or this will destroy the environment")


        instances = cls.get_instances(instance_ids=instance_id, target_tags=target_tags, **kargs)
        if len(instances) == 0 and len(instance_ids) == 0:
            return instances

        ec2 = cls.get_ec2(**kargs)
        instance_ids = [i for i in instances]
        try:
            cls.LOGGER.debug("Attempting to reboot {} instances: {}.".format(len(instance_ids)))
            ec2.reboot_instances(DryRun=dry_run, InstanceIds=instance_ids)
            cls.LOGGER.info("Rebooted instace: {}.".format(vid))
        except KeyboardInterrupt:
            cls.LOGGER.error("Failed to reboot {} instances.".format(len(instance_ids)))
        except:
            cls.LOGGER.error("{}".format(traceback.format_exc()))

        return instances

    @classmethod
    def start_relevant_instances(cls, instance_ids=None, instance_id=None, target_tags: dict=None, dry_run=True, **kargs):
        if instance_ids is None:
            instance_ids = []

        if instance_id not in instance_ids:
            instance_ids.append(instance_id)

        if len(instance_ids) == 0 and (target_tags is None or len(target_tags) == 0):
            cls.LOGGER.critical("WARNING: Must provide tags to filter out instances, or this will destroy the environment")
            raise Exception("Must provide tags to filter out instances, or this will destroy the environment")


        instances = cls.get_instances(instance_ids=instance_id, target_tags=target_tags, **kargs)
        if len(instances) == 0 and len(instance_ids) == 0:
            return instances

        ec2 = cls.get_ec2(**kargs)
        instance_ids = [i for i in instances]
        try:
            cls.LOGGER.debug("Attempting to start {} instances: {}.".format(len(instance_ids)))
            ec2.start_instances(DryRun=dry_run, InstanceIds=instance_ids)
            cls.LOGGER.info("Started instace: {}.".format(vid))
        except KeyboardInterrupt:
            cls.LOGGER.error("Failed to start {} instances.".format(len(instance_ids)))
        except:
            cls.LOGGER.error("{}".format(traceback.format_exc()))

        return instances