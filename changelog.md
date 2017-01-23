# Change Log

This change log only lists the major changes between releases. For a
full list of changes refer to the commit log.

## 2017-01

- New pipelines:
  - chromatin-profiling/chipseq running dfilter and macs2 as well as meme-chip
- Added default SNPeff annotation to all variant callers
- Fasta and bed compatibilty now checked before running
- Added option to skip variant calling in GATK pipeline (--bam-only)
- Added option to use precomputed BAM into GATK pipeline (--raw-bam)
- Added several fixes to fluidigm-ht-c1-rnaseq to be able to robustly deal with the typically huge number of jobs
- Cluster limit adjustements for all pipelines to reflect move from vmem to RSS in GIS, which means more effective use of resources and less chances of collateral damage by misbehaving jobs of other users
- All logs are now automatically bundled on success
- Version upgrades:
  - snakemake 3.8
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
