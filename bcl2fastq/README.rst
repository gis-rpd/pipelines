Description
-----------

This pipeline runs bcl2fastq on the Illumina sequencer
output, by processing MUXes are in parallel.

End-users will not want to use this pipeline! The directory contains
auxiliary scripts used for operations only.


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
- After a successful run the last line in the snakemake log file will say ``(100%) done``
- All output files can be found in ``./out/``
- Furthermore a simple report have been generated (``./out/report.html``)
- Each MUX will have it's own folder there (i.e. ``./out/Project_<MUX>``)
- Each component library of a MUX has its own sub-folder (e.g. ``./out/Project_<MUX>/Sample_<library>``)
- Parameters including program versions etc. can be found in ``conf.yaml``
