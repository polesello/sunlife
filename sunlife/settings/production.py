from .base import *

DEBUG = True
ALLOWED_HOSTS = ['clienti.sunlifegroup.it', 'localhost']

SECRET_KEY = 'Era ora che finissi questo gestionale'

DATABASES['default']['PORT'] = '5432'

try:
    from .local import *
except ImportError:
    pass
