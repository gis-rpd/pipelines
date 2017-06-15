# Change Log

This change log only lists the major changes between releases. For a
full list of changes refer to the commit log.

## 2017-06

New pipelines:
- metagenomics/shotgun-metagenomics: runs several metagenomics
  profilers and pathway analysis
- germs/vipr3: Assembles viral NGS data and analyses low frequency
  variants

Changes to pipelines and framework
- Reduced number of submitted jobs in all pipelines (bundling of jobs
  e.g. in GATK and use of master slot through local rules)
- Reduced cluster memory footprint in all pipelines
- bcl2fastq now also creates index reads by default
- Workflows are restarted automatically once after failure
- S3 suport for FastQ files listed on config files
- Support for injection of processed BAM into GATK and Lacer-LoFreq
- Now using environment modules instead of dotkit

Software Upgrades:
- GATK 3.7
- BWA 0.7.15
- Lacer 0.424
- Snakemake-3.11.2


## 2017-01

- New pipelines:
  - chromatin-profiling/chipseq running dfilter and macs2, followed by meme-chip
- Added default SNPeff annotation to all variant callers
- Fasta and bed compatibility now checked before running
- Added option to skip variant calling in GATK pipeline (--bam-only)
- Added option to use precomputed BAM into GATK pipeline (--raw-bam)
- Several fixes for fluidigm-ht-c1-rnaseq to be able to better deal with the typically huge number of files and jobs
- Cluster limit adjustments for all pipelines to reflect move from vmem to RSS in GIS
- Log files are now automatically bundled on success
- Job completion emails can now be send to other users
- Version upgrades:
  - snakemake 3.8.2
  - sambamba 0.6.5

## 2016-10:

- New pipelines:
  - somatic/lofreq-somatic
  - somatic/mutect
- Update of variant-calling/gatk to GATK 3.6 incl. adoption of new
  best practices (also fixes use of changes known sites according to
  https://software.broadinstitute.org/gatk/guide/article?id=1247)
  - Addition of padding parameter for non-WGS samples
- PCR duplicates are now marked after merging using sambamba
  (previously we used samblaster streaming per fastq pair) in all
  pipelines
- New configuration options: the previously monolithic
  conf.default.yaml was split into references.yaml, modules.yaml and
  params.yaml. These are user changeable via newly added
  parameters. This way one can for example change reference bundles
  etc.
- Multisample support was implemented for most pipelines, with lots of
  internal changes. However, this can lead to surprisingly
  high memory consumption by snakemake itself. See notes in README.md
- Many optimizations (thread settings, cluster settings) and bug-fixes
- Added several of auxiliary tools, e.g. create_mux_cfg.py and whereismux.py
- Added convenience wrapper `run`
- Substantially extended documentation (main README, README per
  pipeline and added example workflow visualizations)
- Reduced all threads to maximum of 16 (NSCC limit 24)
- Refer to git commit messages for more details and changes under the
  hood

## 2016-07:

- newly production ready pipelines
  - BWA-MEM
  - [essential-genes]
  - fluidigm-ht-c1-rnaseq
  - rnaseq
  - variant-calling-gatk
  - variant-calling-lofreq
- new web service: bcl2fastq_record.py
- now using drmaa by default
- simplified wrappers with class PipelineHandler()
- new tools: whatapps and production warnings helper


## 2016-06:

bcl2fastq:
- new `no_archive` option
- mail to ngsp and requestor (`send_email_status.py`)
- new tool: `bcl2fastq_dbrecords.py`
- many bug fixes

## 2016-05

- first ever used deployment
- only bcl2fastq
