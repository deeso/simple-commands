from .consts import *
import paramiko
import scp
import io

class Commands(object):
    @classmethod
    def get_client(cls, host, **kargs):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, **kargs)
        return client

    @classmethod
    def install_docker(cls, host, port=22, key_filename=None, password=None, username=UBUNTU, commands=DOCKER_SETUP_COMMANDS):
        output = []
        client = cls.get_client(host, port=port, key_filename=key_filename, password=password, username=username)
        for cmd in commands:
            _, stdout, stderr = client.exec_command(cmd)
            results = {'command': cmd, 'stdout': None, 'stderr': None}
            results['stdout'] = stdout.read()
            results['stderr'] = stderr.read()
            if debug:
                print(results['stdout'])
            output.append

        print("executed set up commands for {} @ IP addresses: {}".format(len(commands), host))
        stdout.read()
        return output

    @classmethod
    def upload_file(cls, src, dst, host=None, port=22, key_filename=None, password=None, username=UBUNTU, client=None):
        return cls.upload_files({dst:src}, host=host, port=port, key_filename=key_filename, password=password, username=username, client=client)

    @classmethod
    def upload_files(cls, dsts_srcs, host=None, port=22, key_filename=None, password=None, username=UBUNTU, client=None):
        output = []
        client = cls.get_client(host=host, port=port, key_filename=key_filename, password=password, username=username, client=client)
        scp_client = scp.SCPClient(client.get_transport())
        for dst, src in dst_src_buffer.items():
            new_file = open(src, 'rb')
            scp_client.putfo(new_file, dst)            
        return True        

    @classmethod
    def upload_bytes(cls, src_buffer:bytes, dst, host=None, port=22, key_filename=None, password=None, username=UBUNTU, commands=DOCKER_SETUP_COMMANDS):
        return cls.upload_multi_bytes({dst:src_buffer}, host=host, port=port, key_filename=key_filename, password=password, username=username, client=client)

    @classmethod
    def upload_multi_bytes(cls, dst_src_buffer:dict, , host, port=22, key_filename=None, password=None, username=UBUNTU, commands=DOCKER_SETUP_COMMANDS):
        output = []
        client = cls.get_client(host=host, port=port, key_filename=key_filename, password=password, username=username, client=client)
        scp_client = scp.SCPClient(client.get_transport())
        for dst, src_buffer in dst_src_buffer.items():
            new_file = io.BytesIO(src_buffer)
            scp_client.putfo(new_file, dst)            
        return True

    @classmethod
    def execute_commands(cls, commands, client=None, host=None, port=22, key_filename=None, password=None, username=UBUNTU, **cmd_kargs):
        if client is None and host:
            client = cls.get_client(host, port=port, key_filename=key_filename, password=password, username=username)
        elif client is None:
            raise Exception("paramiko.SSHClient or ssh parameters required")

        output = []
        for cmd in commands:
            _, stdout, stderr = client.exec_command(cmd.format(**cmd_kargs))
            results = {'command': cmd, 'stdout': None, 'stderr': None}
            results['stdout'] = stdout.read()
            results['stderr'] = stderr.read()
            if debug:
                print(results['stdout'])
            output.append(results)
        print("executed {} commands".format(len(commands)))
        return results

    @classmethod
    def install_docker(cls, client=None, host=None, port=22, key_filename=None, 
                       password=None, username=UBUNTU, commands=DOCKER_SETUP_COMMANDS):
        output = cls.execute_commands(commands, client=client, host=host, port=port, key_filename=key_filename, password=password, username=username)
        client.close()
        return output

    @classmethod
    def sudo_copy_file(cls, src, dst, client=None, host=None, port=22, 
                  key_filename=None, password=None, username=UBUNTU):
        # src_dst
        src_dst = [{"src":src, 'dst': dst}]
        return cls.sudo_copy_files(src_dst, client=client, host=host, port=port, key_filename=key_filename, password=password, username=username)


    @classmethod
    def sudo_copy_files(cls, src_dst, client=None, host=None, port=22, key_filename=None, password=None, username=UBUNTU):
        commands = [SUDO_COPY_FILE.format(**i) for i in src_dst]
        return cls.exec_commands(client=client, host=host, port=port, key_filename=key_filename, password=password, username=username)
        