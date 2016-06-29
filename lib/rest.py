#!/usr/bin/env python3
"""Imports and parse rest services
"""
import os
import sys
import logging
import yaml
#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
REST_CFG = os.path.join(LIB_PATH, 'rest.yaml')

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)

with open(REST_CFG, 'r') as stream:
    try:
        rest_services = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", REST_CFG)
