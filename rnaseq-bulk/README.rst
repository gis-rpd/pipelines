Description
-----------

This pipeline is for RNASeq bulk analysis and runs STAR, followed by
RNASeQC, RSEM and optionally cuffdiff


How to
------

- Run ``rnaseq-bulk.py -h`` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using ``-v`` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster mode).


Output
------

- The main log file is ``./logs/snakemake.log``
- After a successful run the last line in the snakemake log file will say ``(100%) done``
- All output files can be found in ``./out/``
- Furthermore a simple report have been generated (``./out/report.html``)
- Parameters including program versions etc. can be found in ``conf.yaml``




