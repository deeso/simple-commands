DEFAULT_PORT = 5000

UBUNTU = 'ubuntu'

COPY_FILE = 'sudo cp {src} {dst}'

INSTALL_SYSTEMCTL_COMMANDS = [
    'sudo cp {service_name}.service /lib/systemd/system/',
    'sudo chmod 644 /lib/systemd/system/{service_name}.service',
    'sudo systemctl daemon-reload',
    'sudo systemctl enable {service_name}.service',
    'sudo systemctl start {service_name}.service',
    'sudo systemctl status {service_name}.service'
]

DOCKER_SETUP_COMMANDS = [
    'sudo apt update && sudo apt install -y apt-transport-https ca-certificates curl software-properties-common git python3-pip',
    'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -',
    'sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"',
    'sudo apt update && sudo apt install -y docker-ce docker-compose',
    'sudo usermod -aG docker ${USER}',
]

TAG_MARKER = '--tag-'
TAGS = [('DataClassification', 'None'), 
        ('MailAlias', 'noone@nowhere.org'), 
        ('Name', 'None'), 
        ('ApplicationName', APPLICATION_NAME), 
        ('ResourceOwner', 'None'),
        ('Environment', 'None')
        ]
DEFAULT_TAG_VALUES = {t: v for t, v in TAGS}

TAG_SPECIFICATIONS = [
    {'ResourceType': 'instance',
    'Tags': []
}]


IPIFY_URL = "https://api.ipify.org/?format=json"