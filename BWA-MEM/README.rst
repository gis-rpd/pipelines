Description
-----------

This pipeline maps your reads with BWA-MEM to a reference. Duplicate
reads will be marked by default if not requested otherwise


How to
------

- Run ``BWA-MEM.py -h`` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using ``-v`` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster mode).

Output
------

- The main log file is ``./logs/snakemake.log``
- Each sample will have its own subfolder under ``./out/``
- BAM file(s): ``./out/<sample>/<sample>.bwamem.bam``
- BAM stats: ``./out/<sample>/<sample>.bwamem.bamstats/``
- Parameters including program versions etc. can be found in ``conf.yaml``


