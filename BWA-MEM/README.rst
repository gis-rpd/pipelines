Description
-----------

This pipeline maps reads with BWA-MEM to a given reference. Duplicate
reads will be marked by default, if not requested otherwise.


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
- After a successful run the last line in the snakemake log file will say ``(100%) done``
- Each sample will have its own subfolder under ``./out/``
- Furthermore a simple report have been generated (``./out/report.html``)
- BAM file(s): ``./out/<sample>/<sample>.bwamem.bam``
- BAM stats: ``./out/<sample>/<sample>.bwamem.bamstats/``
- Parameters including program versions etc. can be found in ``conf.yaml``


