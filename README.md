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
  worry about scheduler usage details etc.
- Built-in check-pointing: Easy restart and skipping of already
  completed steps

## Overview

- Each pipeline has its own folder and the corresponding starter
  script has the same name
  (e.g. `variant-calling-gatk/variant-calling-gatk.py`)
- Invoking the starter script with `-h` will display its usage
  information
- Each pipeline folder contains a README file describing the pipeline
  (e.g. `variant-calling-gatk/README.rst`)
- All pipelines are designed to work either the GIS cluster (aquila) or
  the NSCC out of the box
- Upon completion (success or error) an email will be send to the user
  pointing to the output directory
- Should a pipeline fail for technical reasons (crash of a node,
  connectivity issues etc.) they can be easily restarted:: `qsub
  run.sh >> logs/submission.log`. Upon restart, partially created
  files will be automatically deleted and the pipeline will skip
  already completed steps
- Output: results can be found in the respective `./out/`
  sub-directory.  In addition a file called `report.html` will be
  generated containing some basic information about the analysis.
  
## How it works

- All pipelines are based on [![Snakemake](https://img.shields.io/badge/snakemake-≥3.5.2-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)
- Software versions are defined in each pipelines' `conf.default.yaml`
  and loaded via dotkit
- Pipeline wrappers create a run directory which contains all
  necessary configuration files, run scripts etc.
- After creation of this folder the pipeline is automatically
  started/scheduled
- The main log file is `./logs/snakemake.log` (use `tail -f` to follow live progress)
- Cluster log files can be found in the respective `./logs/` sub-directory


## Contact

Writes us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)

