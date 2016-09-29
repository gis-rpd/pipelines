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
- Each pipeline has its own subfolder there and the corresponding wrapper
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

- Find the wrapper of the particular pipeline that you want to run, e.g.: `$PIPELINE_ROOTDIR/variant-calling/gatk/gatk.py`
- Invoke the script with `-h` to display its usage information, e.g. `$PIPELINE_ROOTDIR/variant-calling/gatk/gatk.py -h`
- Note, there is no need to submit the script itself, as long as you run it from a cluster node
- Also note, you must not prefix the script with `python`,
  (installed scripts automatically use the RPD Python3 installation)
- If called correctly, jobs will be run on the cluster automatically
- Use of `-v` is recommended, so that some more information is printed
- All scripts create an output directory (option `-o`) containing the run environment
- Your results will be saved to a corresponding subdirectory called `./out/`
- Upon completion (success or error) an email will be send to the user
  (unless `--no-mail` was specified) pointing to the results. In addition a file called `report.html`
  will be generated containing some basic information about the
  analysis.
- Should a pipeline fail for purely technical reasons (crash of a
  node, connectivity issues etc.) they can be easily restarted: cd
  into the output directory and `qsub run.sh >>
  logs/submission.log` (for GIS). Upon restart, partially created files will be
  automatically deleted and the pipeline will skip already completed
  steps
- Note, that the output directory has to be on a filesystem shared by
  the cluster (i.e. local /tmp wont't work unless run in local mode)

### Example

#### Variant calling with GATK for an Exome sample with two fastq pairs

    fq1_x=x_R1.fastq.gz
    fq2_x=x_R2.fastq.gz
    fq1_y=y_R1.fastq.gz
    fq2_y=y_R2.fastq.gz    
    variant-calling/gatk/gatk.py -o /output-folder-for-this-analysis/ -1 $fq1_x $fq1_y -2 $fq2_x $fq2_y -s sample-name -t WES -l SeqCap_EZ_Exome_v3_primary.bed

## How it Works

- All pipelines are based on [![Snakemake](https://img.shields.io/badge/snakemake-≥3.5.2-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)
- Input will be a single fastq file or a pair of fastq files. Multiple of these can
  be given. Each pair is treated as one readunit (see also resulting
  `conf.yaml` file) and gets its own readgroup assigned were
  appropriate.
- Software versions are defined in each pipelines' `cfg/modules.yaml`
  and loaded via [dotkit](https://computing.llnl.gov/?set=jobs&page=dotkit)
- Pipeline wrappers create an output directory containing all
  necessary configuration files, run scripts etc.
- After creation of this folder, the analysis run is automatically submitted to the cluster
 (unless `--no-run` was used which gives you a chance to change the config file `conf.yaml`)
- The actual run script is called `run.sh`
- The main log file is `./logs/snakemake.log` (use `tail -f` to follow live progress)
- After a successful run the last line in the snakemake log file will
  say `(100%) done`
- Cluster log files can be found in the respective `./logs/` sub-directory


## Debugging Techniques

Call a wrapper with `--no-run` and
- Check the created `conf.yaml`
- Execute a dryrun: `EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh; cat logs/snakemake.log`
- Run locally: `nohup bash run.sh; tail -f logs/snakemake.log`



## List of Pipelines


- [bcl2fastq](bcl2fastq/README.md) (production use only)
- custom
  - [SG10K](custom/SG10K/README.md)
- mapping
  - [BWA-MEM](mapping/BWA-MEM/README.md)
- metagenomics
  - [essential-genes](metagenomics/essential-genes/README.md)
- rnaseq
  - [star-rsem](rnaseq/fluidigm-ht-c1-rnaseq/README.md)
  - [fluidigm-ht-c1-rnaseq](rnaseq/star-rsem/README.md)
- somatic
  - [lofreq-somatic](somatic/lofreq-somatic/README.md)
  - [mutect](somatic/mutect/README.md)
- variant-calling
  - [gatk](variant-calling/gatk/README.md)
  - [lacer-lofreq](variant-calling/lacer-lofreq/README.md)


## FAQ

#### Where are my results?

In the output directory that you specified with `-o`, under a
subdirectory called `out`. Depending on the pipeline, the samplename
is added as well.

#### How do I know the pipeline run is completed?

You should have received an email. To double check run `tail
logs/snakemake.log` in the output directory. It should either say
`Nothing to be done` or `(100%) done`

#### How do I submit the wrapper to the cluster?

You don't. It's taken care of automatically.

#### Which Python version should I use?

Nevermind. Just call the wrapper without using `python`.

#### Pipeline execution failed. What now?

First, simply try to restart the pipeline. In your output directory
execute `qsub run.sh >> logs/submission.log`.

If this still fails, you need to troubleshoot by examining the log
files. You can ask us for help (see below).

#### Can you write a pipeline for me?

In theory yes. Please email us. A committee will decide on
implementation priority.

#### Can these pipelines be selected in / run from ELM?

No and they never will be. We'll provide a separate webinterface for
launching soon.  For now you will have to use the commandline.

## Comments, Questions, Bug reports

Contact us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)
