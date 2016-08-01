#!/usr/bin/env python3
"""Imports and parse rest services
"""

# standard library imports
import os
import sys
import logging

# third party imports
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
ETC_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "etc"))
    
REST_CFG = os.path.join(ETC_PATH, 'rest.yaml')
MAIL_CFG = os.path.join(ETC_PATH, 'mail.yaml')
MONGO_CFG = os.path.join(ETC_PATH, 'mongo.yaml')


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
        logger.fatal("Error loading %s", REST_CFG)
        raise
    
with open(MAIL_CFG, 'r') as stream:
    try:
        SMTP_SERVER = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", MAIL_CFG)
        raise

with open(MONGO_CFG, 'r') as stream:
    try:
        mongo_conns = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", MONGO_CFG)
        raise
    
