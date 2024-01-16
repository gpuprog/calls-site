import sys
import os
import re

FILE_PATH = os.path.dirname(__file__)
ENVS_FILE = os.path.join(FILE_PATH, '.envs')

ln = 1
with open(ENVS_FILE, 'r') as envs:
    for line in envs:
        match = re.search("([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*'?([^'\n]+)'?\s*$", line)
        if match:
            var = match.group(1)
            val = match.group(2)
        if match is None or var is None or len(var)==0 or val is None:
            raise Exception(f'Wrong syntax in line {ln} of {ENVS_FILE}: {var}={val}')
        os.environ[var] = val

sys.path.insert(0, os.path.join(FILE_PATH, '.'))
sys.path.insert(0, os.path.join(FILE_PATH, 'webgui'))
from wsgi import application
