import os
import boto3

class Commands(object):
    AWS_SECRET_ACCESS_KEY = None
    AWS_ACCESS_KEY_ID = None
    DEFAULT_REGION=None

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
    def extract_tags(cls, **kargs):
        tags = DEFAULT_TAG_VALUES.copy()
        for k, v in kargs.items():
            if k in tags:
                tags[k] = v
        return tags

    @classmethod
    def configure_tags(cls, **kargs):
        tags = extract_tags(**kargs)

        tags_specs = [{'Key':k, 'Value': v} for k, v in tags.items()]
        tag_specification = TAG_SPECIFICATIONS.copy()
        tag_specification[0]['Tags'] = tags_specs
        return tag_specification
    
    @classmethod
    def get_ec2(cls, ec2=None, region=DEFAULT_REGION, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_access_key_id=AWS_ACCESS_KEY_ID, **kargs):
        if ec2 is None:
            ec2 = boto3.client('ec2', 
                           region, 
                           aws_access_key_id=aws_access_key_id, 
                           aws_secret_access_key=aws_secret_access_key)
        return ec2


    @classmethod
    def get_key_pair(key_name, key_path, recreate=False, **kargs):
        ec2 = cls.get_ec2(**kargs)
        key_filename = os.path.join(key_path, key_name)
        try:
            ec2.describe_key_pairs(KeyNames=[key_name])
            if os.path.exists(key_path) and not recreate:
                return key_filename
            elif recreate:
                ec2.delete_key_pair(KeyName=key_name)
        except:
            pass

        try:
            os.chmod(key_filename, 0o600)
            os.remove(key_filename)
            
        except:
            pass

        outfile = open(key_filename,'w')
        key_pair = ec2.create_key_pair(KeyName=key_name)
        KeyPairOut = str(key_pair['KeyMaterial'])
        outfile.write(KeyPairOut)
        outfile.close()
        os.chmod(key_filename, 0o600)
        return key_filename

    @classmethod
    def create_security_group(ec2, sg_name, sg_description, ingress, **kargs):
        ec2 = cls.get_ec2(**kargs)
        try:
            rsp = ec2.describe_security_groups(GroupNames=[sg_name])
            return rsp['SecurityGroups'][0]['GroupId']
        except:
            pass

        rsp = ec2.create_security_group(GroupName=sg_name,
                                             Description=sg_description)
        sg_id = rsp.get('GroupId', None)
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=ingress)
        return sg_id

    @classmethod
    def create_instances(cls, key_name, max_count=1, image_id, instance_type, security_groups, 
                         tag_specifications, **kargs):
        
        ec2 = cls.get_ec2(**kargs)

        reservations = ec2.run_instances(
            DryRun=False, 
            MinCount=1, 
            MaxCount=max_count, 
            ImageId=image_id, 
            KeyName=key_name, 
            InstanceType=instance_type, 
            SecurityGroups=security_groups, 
            TagSpecifications=tag_specifications
        ) 

        instances = [i['InstanceId'] for i in reservations['Instances']]
        return instances

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

            print ("Instance appears to have completed loading:", instance_id)
            instances_completed_loading.append(instance_id)
        return instances_completed_loading

    @classmethod
    def get_instance_public_ips(cls, instances, **kargs):
        ec2 = cls.get_ec2(**kargs)
        results = ec2.describe_instances(InstanceIds=instances)
        instance_infos = []
        for k in results['Reservations']:
            instance_infos = instance_infos + k['Instances']
        
        instance_to_ip = {k['InstanceId']: k.get('PublicIpAddress', '') for k in instance_infos}
        return instance_to_ip

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
    def find_relevant_instances_multiple_regions(cls, target_tags: dict=None, regions=DCS, **kargs):
        target_tags = target_tags if target_tags else {}
        relevant_instances = []
        for region in regions:
            instances = cls.find_relevant_instances(region=region, target_tags=target_tags, **kargs)
            relevant_instances.append({'region': region, 'instances': instances})
        return relevant_instances

    @classmethod
    def terminate_relevant_instances(cls, target_tags: dict=None, dry_run=True, **kargs):
        if target_tags is None or len(target_tags) == 0:
            raise Exception("Must provide tags to filter out instances, or this will destroy the environment")

        instances = cls.find_relevant_instances(target_tags=target_tags, **kargs)
        if len(instances) == 0:
            return instances

        ec2 = cls.get_ec2(**kargs)
        try:
            instance_ids = [i for i in instances]
            ec2.terminate_instances(DryRun=dry_run, InstanceIds=instance_ids)
        except:
            raise

        return instances

    @classmethod
    def terminate_relevant_instances_multiple_regions(cls, regions=DCS, dry_run=True, **kargs):
        relevant_instances = []
        for region in regions:
            results = cls.terminate_relevant_instances(region=region, dry_run=dry_run, **kargs)
            relevant_instances.append({'region': region, 'instances': results})
        return relevant_instances