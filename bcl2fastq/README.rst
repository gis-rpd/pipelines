Description
-----------

This pipeline runs bcl2fastq on the raw Illumina sequencer
output. Each MUX is processed individually.

End-users will most likely not want to use this pipeline! The
directory contains plenty of auxiliary scripts used for operations
only.


How to
------

- Run `./bcl2fastq/bcl2fastq.py -h` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using ``-v`` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster
  mode).  Note that a crash due to input file or parameter issues can
  not be resolved in this fashion.


  Output
------

- The main log file is ``./logs/snakemake.log``
- All output files can be found in ``./out/``
- Parameters including program versions etc. can be found in ``conf.yaml``




