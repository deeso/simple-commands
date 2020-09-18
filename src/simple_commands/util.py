import os
import tempfile
import socket
import string
import json
import hashlib
import random
from datetime import datetime
import uuid
import requests
import netifaces

from .consts import *

get_server_date = lambda : datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
get_docker_id = lambda : hashlib.sha256(get_server_date().encode('ascii')).hexdigest()
get_random_data = lambda : random_string_generator()
get_iso_time = lambda: datetime.now().isoformat()

def create_token(iters=1):
    return "-".join([str(uuid.uuid4()) for i in range(0, iters)])

def random_string_generator(str_size=25, allowed_chars=string.ascii_letters + string.punctuation):
    return ''.join(random.choice(allowed_chars) for x in range(str_size))

def get_external_ip():
    ext_ip = ''

    gws = netifaces.gateways()
    dft = gws.get('default', {})
    g = sorted(dft.items(), key=lambda k: k[0])
    if len(g) > 0:
        ext_ip = g[0][1][0]
    
    try:
        ext_ip = requests.get(IPIFY_URL).json()['ip']
    except:
        pass
    return ext_ip


def get_stream_logger(name, level=level.DEBUG, lformat=STANDARD_FORMAT):
    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # create formatter
    formatter = logging.Formatter(lformat)

    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    return logger

def reset_logger_level(logger, level):
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
    return logger