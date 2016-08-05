# NGS Pipeline Framework for [GIS](https://www.a-star.edu.sg/gis/)


This folder contains workflows/pipelines developed and maintained by
the
[Research Pipeline Development Team (RPD)](https://www.a-star.edu.sg/gis/our-science/technology-platforms/scientific-and-research-computing-platform.aspx)


## Features

- Pipelines are divided into steps that are automatically run in parallel
  whenever possible so that each step makes optimal use of resources
- Pipelines work out of the box on the GIS in-house cluster (aquila)
  and the
  [National Super Computing Center (NSCC)](http://help.nscc.sg/)
  without any changes required by the user
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
  pointing to results (or log files)
- Output: results can be found in the respective `./out/`
  sub-directory.  In addition a file called `report.html` will be
  generated containing some basic information about the analysis.
- Should a pipeline fail for purely technical reasons (crash of a
  node, connectivity issues etc.) they can be easily restarted: cd
  into the output directory and `qsub run.sh >>
  logs/submission.log`. Upon restart, partially created files will be
  automatically deleted and the pipeline will skip already completed
  steps
- In GIS different pipeline versions are installed at ``/mnt/projects/rpd/pipelines/``
  
## How it works

- All pipelines are based on [![Snakemake](https://img.shields.io/badge/snakemake-≥3.5.2-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)
- Software versions are defined in each pipelines' `conf.default.yaml`
  and loaded via [dotkit](https://computing.llnl.gov/?set=jobs&page=dotkit)
- Pipeline wrappers create a run directory which contains all
  necessary configuration files, run scripts etc.
- After creation of this folder, the pipeline is automatically
  scheduled (unless `--no-run` was used which gives you a chance to change the config file `conf.yaml`)
- The main log file is `./logs/snakemake.log` (use `tail -f` to follow live progress)
- Cluster log files can be found in the respective `./logs/` sub-directory


## List of Pipelines


- bcl2fastq
- custom
  - SG10K
- mapping
  - BWA-MEM
- metagenomics
  - essential-genes
- rnaseq
  - star-rsem
  - fluidigm-ht-c1-rnaseq
- variant-calling
  - gatk
  - lacer-lofreq


## One wrapper, multiple samples

If you want to analyze many samples (identically) with just one
wrapper call, you will have to provide per sample information to the
wrapper. The easiest way to achieve this, is to create an Excel sheet
listing all samples and fastq pairs and converting it into a config
file as described in the following:

- Create an Excel sheet with the following columns:
  1. sample name (mandatory; can be used repeatedly, e.g. if you have multiple fastqs per sample)
  2. run id (allowed to be empty)
  3. flowcell id (allowed to be empty)
  4. library id (allowed to be empty)
  5. lane id (allowed to be empty)
  6. read-group id (allowed to be empty)
  7. fastq1 (mandatory)
  8. fastq2 (allowed to be empty)
- Save the Excel sheet as CSV and run the following script on it:
  `tools/sample_conf.py -i <your>.csv -i <your>.yaml`
  Depending on how you created the CSV file you might want to set the CSV delimiter with `-d`, e.g. `-d ,`
- Use the created yaml files as input for the pipeline wrapper (`-c your.yaml`)

## Comments, Questions, Bug reports

Contact us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)


## Note to non-GIS Users

Much of this framework assumes a certain setup and services to be
present, as is the case in GIS. In other words, it might be of limited
use to the general public. See INSTALL.md for simplistic installation
instructions.
