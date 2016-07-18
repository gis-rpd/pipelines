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

- Pipelines are organized into directories of specific category,
  e.g. `variant-calling`
- Each pipeline has its own subfolder there and the corresponding starter
  script has the same name
  (e.g. `variant-calling/gatk/gatk.py`)
- All wrappers require Python3. Should it be required, add the RPD Python
  installation to your PATH: `export
  PATH=/mnt/projects/rpd/apps/miniconda3/bin/:$PATH`
- Invoking the starter script with `-h` will display its usage
  information
- Each pipeline folder contains a README file (`README.rst` and/or
  `README.html`) describing the pipeline
  (e.g. `variant-calling/gatk/README.rst`)
- All pipelines are designed to work either on aquila (UGE) or
  the NSCC (PBSPro) out of the box
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
- After creation of this folder, the pipeline is automatically
  scheduled (unless `--no-run` was used)
- The main log file is `./logs/snakemake.log` (use `tail -f` to follow live progress)
- Cluster log files can be found in the respective `./logs/` sub-directory


## Comments, Questions, Bug reports

Contact us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)

