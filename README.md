# NGS Pipeline Framework for [GIS](https://www.a-star.edu.sg/gis/)


This folder contains workflows/pipelines developed and maintained by
the
[Research Pipeline Development Team (RPD)](https://www.a-star.edu.sg/gis/our-science/technology-platforms/scientific-and-research-computing-platform.aspx)


## Features

- Cluster specifics are handled internally, i.e. users don't have to
  worry about scheduler usage details etc.
- Built-in check-pointing: Easy restart and skipping of already
  completed steps
- Pipelines work out of the box on GIS's aquila (UGE) or the
  [National Super Computing Center (NSCC)](http://help.nscc.sg/) (PBS Pro)
  without any changes required by the user
- Pipelines are divided into steps that are automatically run in parallel
  where possible and each step tries to make optimal use of resources

## Overview

- Pipelines are organized into directories of specific category,
  e.g. `variant-calling`
- Each pipeline has its own subfolder there and the corresponding starter
  script has the same name
  (e.g. `variant-calling/gatk/gatk.py`)
- Each pipeline folder contains a README file (`README.rst` and/or
  `README.html`) describing the pipeline
  (e.g. [`variant-calling/gatk/README.rst`](variant-calling/gatk/README.rst))

## Installation

The following installations are available at different sites (referred to as `RPD_PIPELINES` below):
- GIS: `/mnt/projects/rpd/pipelines/`
- NSCC: `/seq/astar/gis/rpd/pipelines/`

Each of these contains one subfolder per pipeline version,
e.g. `$RPD_PIPELINES/pipelines.2016-07` (referred to as
`PIPELINE_ROOTDIR` below).

Much of this framework assumes a certain setup and services to be
present, as is the case in GIS / the NSCC. This repository is
therefore of limited use to the general public. See INSTALL.md for
simplistic installation instructions.

## How to Run

- Chose the wrapper of a particular pipeline that you want to run, e.g.: `$PIPELINE_ROOTDIR/variant-calling/gatk/gatk.py`
- Invoke the wrapper with `-h` to display its usage information, e.g. `$PIPELINE_ROOTDIR/variant-calling/gatk/gatk.py -h`
- Note, there is no need to submit the wrapper itself, as long as you run the wrapper from a cluster node
- Also note, you must not prefix the wrapper command with `python`,
  (installed wrappers automatically use the RPD Python3 installation)
- All wrappers create an output directory (option `-o`) containing the run environment
- Your results will be saved to a corresponding subdirectory called `./out/`
- Upon completion (success or error) an email will be send to the user
  pointing to the results.  In addition a file called `report.html`
  will be generated containing some basic information about the
  analysis.
- Should a pipeline fail for purely technical reasons (crash of a
  node, connectivity issues etc.) they can be easily restarted: cd
  into the output directory and `qsub run.sh >>
  logs/submission.log` (for GIS). Upon restart, partially created files will be
  automatically deleted and the pipeline will skip already completed
  steps
  
## How it Works

- All pipelines are based on [![Snakemake](https://img.shields.io/badge/snakemake-≥3.5.2-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)
- Software versions are defined in each pipelines' `cfg/modules.yaml`
  and loaded via [dotkit](https://computing.llnl.gov/?set=jobs&page=dotkit)
- Pipeline wrappers create an output directory containing all
  necessary configuration files, run scripts etc.
- After creation of this folder, the analysis run is automatically
  submitted (unless `--no-run` was used which gives you a chance to change the config file `conf.yaml`)
- The main log file is `./logs/snakemake.log` (use `tail -f` to follow live progress)
- Cluster log files can be found in the respective `./logs/` sub-directory
- For debugging prupose

## Debugging Techniques

Call a wrapper with `--no-run` and
- Check the created `conf/yaml`
- Execute a dryrun: `EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh; cat logs/snakemake.log`
- Run locally: `nohup bash run.sh; tail -f logs/snakemake.log`



## List of Pipelines


- bcl2fastq (production use only)
- custom
  - SG10K (specialized use only)
- mapping
  - BWA-MEM
- metagenomics
  - essential-genes
- rnaseq
  - star-rsem
  - fluidigm-ht-c1-rnaseq
- somatic
  - lofreq-somatic
  - mutect
- variant-calling
  - gatk
  - lacer-lofreq


## Comments, Questions, Bug reports

Contact us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)

