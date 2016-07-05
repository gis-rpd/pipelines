Description
-----------

This pipeline runs bcl2fastq on the raw Illumina sequencer
output. Each MUX is processed individually.

End-users will most likely not want to use this pipeline! The
directory contains plenty of auxiliary scripts used for operations
only.

All runtime variables can be found in `conf.yaml`


How to
------

- Run `./bcl2fastq/bcl2fastq.py -h` to get basic usage information.
- Using -v is recommended to get some more information
- If called correctly, jobs will be run on the cluster automatically
- Should the pipeline 'crash', it can be restarted by simply running
  `bash run.sh` (for local mode) or `qsub run.sh` (for cluster mode).
- All log files can be found in `./logs/`
- All output files can be found in `./out/`




