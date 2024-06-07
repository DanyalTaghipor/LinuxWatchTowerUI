from enum import Enum

class Tools(Enum):
    NGINX = {'default': 'nginx', 'versions': ['latest']}
    APACHE = {'default': 'apache', 'versions': ['latest']}