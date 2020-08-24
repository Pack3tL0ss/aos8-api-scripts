#!/usr/bin/env python3
#
# Author: Wade Wells github/Pack3tL0ss

import os
import yaml


def get_yaml_file(yaml_file):
    '''Return dict from yaml file.'''
    if os.path.isfile(yaml_file) and os.stat(yaml_file).st_size > 0:
        with open(yaml_file) as f:
            try:
                # return yaml.load(f, Loader=yaml.BaseLoader)
                return yaml.load(f, Loader=yaml.SafeLoader)
            except ValueError as e:
                print(f'Unable to load configuration from {yaml_file}\n\t{e}', show=True)