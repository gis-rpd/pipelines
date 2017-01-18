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
    
SITE_CFG_FILE = os.path.join(ETC_PATH, 'site.yaml')
REST_CFG_FILE = os.path.join(ETC_PATH, 'rest.yaml')
MONGO_CFG_FILE = os.path.join(ETC_PATH, 'mongo.yaml')
BCL2FASTQQC_CFG_FILE = os.path.join(ETC_PATH, 'bcl2fastq_qc.yaml')
LEGACY_MAPPER_CFG_FILE = os.path.join(ETC_PATH, 'legacy_wrapper.yaml')

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)

with open(SITE_CFG_FILE, 'r') as stream:
    try:
        site_cfg = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", SITE_CFG_FILE)
        raise

with open(REST_CFG_FILE, 'r') as stream:
    try:
        rest_services = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error loading %s", REST_CFG_FILE)
        raise
    
with open(BCL2FASTQQC_CFG_FILE, 'r') as stream:
    try:
        bcl2fastq_qc_conf = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", BCL2FASTQQC_CFG_FILE)
        raise
with open(MONGO_CFG_FILE, 'r') as stream:
    try:
        mongo_conns = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", MONGO_CFG_FILE)
        raise

with open(LEGACY_MAPPER_CFG_FILE, 'r') as stream:
    try:
        legacy_mapper = yaml.load(stream)
    except yaml.YAMLError as exc:
        logger.fatal("Error in loading %s", LEGACY_MAPPER_CFG_FILE)
        raise
