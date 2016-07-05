# RPD Pipelines for GIS 


This folder contains workflows/pipelines developed and maintained by
the
[Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg).


## Features

- Pipelines are divided into steps that are automatically run in parallel
  whereever possible and each step makes optimal use of resources
- Pipelines work out of the box on the GIS in-house cluster (aquila) and the
  NSCC without any changes required by the user
- Cluster specifics are handled internally, i.e. users don't have to
  worry about exact schedule usage etc.
- Built-in check-pointing: Easy restart and skipping of already
  completed steps

## Overview

- Each pipeline has its own folder (e.g. `variant-calling-gatk`) and
  the corresponding starter script has the same name
  (e.g. `variant-calling-gatk/variant-calling-gatk.py`)
- Invoking the starter script with `-h` will display its usage
  information
- Each pipeline folder contains a document describing the pipeline (`README.rst`) 
- All pipeline are designed to work either the GIS cluster (aquila) or
  the NSCC without changes required by the users
- Upon completion (success or error) an email will be send to the user
  pointing to the output directory
- Should a pipeline fail for purely technical reasons (problems on a
  particular node,connectivity issues etc.) they can be easily
  restarted (use: `qsub run.sh >> logs/submission.log`). Upon restart,
  partially created files will be automatically deleted and the
  pipeline will skip already completed steps

## How it works

- Pipelines are based on the [Snakemake](http://snakemake.bitbucket.org) workflow manager
- Software versions are defined in each pipelines' `conf.default.yaml` and loaded via dotkit
- The pipeline wrappers create a run directory which contains all necessary configuration files, run scripts etc.
- After creation of this folder the pipeline is automatically started/scheduled
- Log files can be found in the respectives `logs` sub-directory
- Results files can be found in the respectives `out` sub-directory

[![Snakemake](https://img.shields.io/badge/snakemake-≥3.5.2-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)


## Contact

Writes us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)

