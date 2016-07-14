# Change Log

This change log only lists the major changes between releases. For a
full list of changes refer to the commit log.

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
