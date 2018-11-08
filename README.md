# NGS Pipeline Framework for [GIS](https://www.a-star.edu.sg/gis/)


This folder contains workflow developed by
the
[Research Pipeline Development Team (RPD)](https://www.a-star.edu.sg/gis/our-science/technology-platforms/scientific-and-research-computing-platform.aspx)


## Features

- Cluster specifics are handled internally, i.e. users don't have to
  worry about scheduler usage.
- Built-in check-pointing: Easy restart and skipping of already
  completed steps
- Pipelines work out of the box on GIS's aquila (UGE) or the
  [National Super Computing Center (NSCC)](http://help.nscc.sg/) (PBS Pro)
  without any changes required by the user
- Pipelines are divided into steps that are automatically run in parallel
  where possible and each step tries to make optimal use of resources

## Overview

- Pipelines are organised into directories of specific category,
  e.g. `variant-calling`
- Each pipeline has its own subfolder there and the corresponding wrapper
  script has the same name
  (e.g. `variant-calling/gatk/gatk.py`)
- Each pipeline folder contains a README file describing the pipeline
  (e.g. [`variant-calling/gatk/README.md`](variant-calling/gatk/README.md))
- Furthermore, each pipeline folder contains an example flowchart of
  the workflow, called `example-dag.pdf` (see
  e.g. [`variant-calling/gatk/example-dag.pdf`](variant-calling/gatk/example-dag.pdf))
  
  
## Existing Installations

The following installations are available at different sites (referred to as `RPD_PIPELINES` below):
- GIS: `/mnt/projects/rpd/pipelines/`
- NSCC: `/data/users/astar/gis/rpd/pipelines/`

Each of these contains one subfolder per pipeline version,
e.g. `$RPD_PIPELINES/pipelines.2017-06` (referred to as
`PIPELINE_ROOTDIR` below).

Much of this framework assumes a certain setup and services to be
present, as is the case in GIS / the NSCC. This repository is
therefore of limited use to the general public. See `INSTALL.md` for
simplistic installation instructions.

Some pipelines only work at a certain site (due to system or software
incompatibilities etc.). Refer to the table of pipelines below for
details regarding availability.

## How to Run

There are two ways to invoke a pipeline: either call the convenience
wrapper, plainly called `run` or invoke the pipeline specific scripts
directly:

1. Using the convenience wrapper (recommended)
  - The basic usage is `$PIPELINE_ROOTDIR/run name options`, where
    `name` is a pipeline name and `options` are valid options for this
    pipeline.
  - An example (GATK) would be `$PIPELINE_ROOTDIR/run gatk --help`
  - Just calling `$PIPELINE_ROOTDIR/run` will print a list of
    available pipelines and simple usage information
2. Direct invocation
  - Directly call the wrapper of the particular pipeline that you want
    to run, e.g. for GATK: `$PIPELINE_ROOTDIR/variant-calling/gatk/gatk.py`
  - Note, in this case you need to have a Python3 interpreter in your
    PATH, which is not needed if you use the convenience wrapper (see
    above)
    
    
In either case, you must not prefix the script with `python`.

- Note, there is no need to submit the script itself, as long as you
  run it from a cluster node
- If called correctly, jobs will be run on the cluster automatically
- Use `-h` or `--help` to display usage information
- Use the `-v` option, so that more information is printed
- All scripts create an output directory (option `-o`) containing the run environment
- Your results will be saved to a corresponding subdirectory called `./out/`
- Upon completion (success or error) an email will be send to the user
  (unless `--no-mail` was specified) pointing to the results. In addition a file called `report.html`
  will be generated containing some basic information about the
  analysis.
- Should a pipeline fail for technical reasons (crash of a
  node, connectivity issues etc.) they can be easily restarted: cd
  into the output directory and `qsub run.sh >>
  logs/submission.log`. Upon restart, partially created files will be
  automatically deleted and the pipeline will skip already completed
  steps
- Note, that the output directory has to be on a shared file-system,
  i.e. directories local to the cluster node like `/tmp` won't work,
  unless run in local mode)

### Example

#### Variant calling with GATK for an Exome sample with two FastQ pairs

    fq1_x=x_R1.fastq.gz
    fq2_x=x_R2.fastq.gz
    fq1_y=y_R1.fastq.gz
    fq2_y=y_R2.fastq.gz
    bed=/path/to/SeqCap_EZ_Exome_v3_primary.bed
    outdir=/path/to/output-folder-for-this-analysis/
    /path/to/pipelines/run gatk -o $outdir -1 $fq1_x $fq1_y -2 $fq2_x $fq2_y -s sample-name -t WES -l $bed
    # or
    # /path/to/pipelines/variant-calling/gatk/gatk.py -o $outdir -1 $fq1_x $fq1_y -2 $fq2_x $fq2_y -s sample-name -t WES -l $bed
    

## List of Pipelines

| Name | Category | Notes | @GIS | @NSCC |
| ---  | ---      | ---   | ---  | ---   |
| [bcl2fastq](bcl2fastq/README.md)            | Production          | Not for end-users     | Y | Y |
| [ATAC-seq](chromatin-profiling/atacseq/README.md)             | Chromatin Profiling |                       | Y | Y |
| [ChIP-seq](chromatin-profiling/chipseq/README.md)             | Chromatin Profiling |                       | Y | Y |
| [SG10K](custom/SG10K/README.md)                | Custom              | Not for end-users     | Y | Y |
| [ViPR](germs/vipr/README.md)                 | GERMS               |                       | Y | Y |
| [BWA-MEM](mapping/BWA-MEM/README.md)              | Mapping             |                       | Y | Y |
| [Shotgun Metagenomics](metagenomics/shotgun-metagenomics/README.md) | Metagenomics        |                       | Y | Y |
| [Essential-Genes](metagenomics/essential-genes/README.md)      | Metagenomics        | Requires ref download | Y | Y |
| [STAR-RSEM](rnaseq/star-rsem/README.md)            | RNA-Seq             |                       | Y | Y |
| [Fluidigm-HT-C1-RNASeq](rnaseq/fluidigm-ht-c1-rnaseq/README.md)| RNA-Seq             |                       | Y | N |
| [Wafergen-scRNA](rnaseq/wafergen-scrna/README.md)       | RNA-Seq             | Requires cellular barcodes | Y | Y |
| [LoFreq-Somatic](somatic/lofreq-somatic/README.md)       | Somatic             |                            | Y | N |
| [Mutect](somatic/mutect/README.md)               | Somatic             |                            | Y | Y |
| [GATK](variant-calling/gatk/README.md)                 | Variant-calling     |                            | Y | Y |
| [Lacer-LoFreq](variant-calling/lacer-lofreq/README.md)         | Variant-calling     |                            | Y | N |

See `example-dag.pdf` in each pipeline's folder for a visual overview of the workflow.

Note, most pipelines start with FastQ files as input, a few allow injection of BAM files.

## How it Works

- All pipelines are based on [![Snakemake](https://img.shields.io/badge/snakemake-≥3.7.1-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)
- Input will be a single FastQ file or a pair of FastQ files. Multiple of these can
  be given. Each pair is treated as one readunit (see also resulting
  `conf.yaml` file) and gets its own read-group assigned where
  appropriate.
- Software versions are defined in each pipelines' `cfg/modules.yaml`
  and loaded via [Lmod](http://lmod.readthedocs.io/en/latest/)
- Pipeline wrappers create an output directory containing all
  necessary configuration files, run scripts etc.
- After creation of this folder, the analysis run is automatically submitted to the cluster
 (unless `--no-run` was used which gives you a chance to change the config file `conf.yaml`)
- The actual run script is called `run.sh`
- The main log file is `./logs/snakemake.log` (use `tail -f` to follow live progress)
- After a successful run, the last line in the mail log file will
  read: `(100%) done`
- Cluster log files can be found in the respective `./logs/` sub-directory


## Debugging Techniques

First call the wrapper in question with `--no-run`. cd into the given outdir and then
- Check the created `conf.yaml`
- Execute a dryrun: `rm -f logs/snakemake.log; EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh; cat logs/snakemake.log`
- Run locally: `nohup bash run.sh; tail -f logs/snakemake.log`


## (Multi) Sample Configuration

If you have just one sample to analyse (no matter if multiple FastQ
pairs or not), you will use options `-s`, `-1` and `-2` most of the
time. To provide the pipeline with more information about your FastQ
files (e.g. run-id etc.) you can create a sample configuration file
(see below) and provide it to the wrapper script with `--sample-cfg`
(thus replacing `-s`, `-1` and `-2`).

You also need a sample configuration file if you want to analyse many
samples identically with just one wrapper call. The easiest way to
create such a file is to first create an Excel/CSV sheet listing all
samples and FastQ files and convert it into a sample config file as
described in the following:

- Create an Excel sheet with the following columns:
  1. sample name (mandatory; can be used repeatedly, e.g. if you have multiple FastQs per sample)
  2. run id (allowed to be empty)
  3. flowcell id (allowed to be empty)
  4. library id (allowed to be empty)
  5. lane id (allowed to be empty)
  6. read-group id (allowed to be empty)
  7. fastq1 (mandatory)
  8. fastq2 (allowed to be empty)
- Save the Excel sheet as CSV and run the following to convert it to a
  yaml config file: `tools/sample_conf.py -i <your>.csv -i
  <your>.yaml` Depending on how you created the CSV file you might
  want to set the CSV delimiter with `-d`, e.g. `-d ,`
- Use the created yaml file as input for the pipeline wrapper (option `--sample-cfg your.yaml`)

Please note, not all pipelines support this feature, for example the
Chipseq and all somatic pipelines. In some cases multisample
processing can lead to very high memory consumption by the snakemake
master process itself, a side-effect which is hard to predict (the
master process will be killed).

The above configuration can be used for single sample processing as
well, however, for single samples the corresponding use of options
`-s`, `-1` and `-2` is usually easier.

## FAQ

#### Where are my results?

In the output directory that you specified with `-o`, under a
subdirectory called `out`. Depending on the pipeline, the sample-name
is added as well.

#### How do I know the pipeline run is completed?

You should have received an email. To double check run `tail
logs/snakemake.log` in the output directory. It should either say
`Nothing to be done` or `(100%) done`

#### How do I submit the wrapper to the cluster?

You don't. It's taken care of automatically.

#### Which Python version should I use?

None! Call scripts directly, i.e. without `python`.

#### Pipeline execution failed. What now?

First, simply try to restart the pipeline. In your output directory
execute `qsub run.sh >> logs/submission.log`.

If this still fails, you need to troubleshoot by examining the log
files. You can ask us for help (see below).

#### Can you write a pipeline for me?

Yes. Please email us. A committee will decide on
implementation priority.

#### Can these pipelines be selected in / run from ELM?

No. For now you will have to use the commandline. The Datahub team is
working on a separate web-interface for running pipelines.

## Comments,

For questions, feedback, bug reports etc. contact us: [Research Pipeline Development Team (RPD)](mailto:rpd@gis.a-star.edu.sg)
