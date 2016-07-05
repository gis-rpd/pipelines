Description
-----------

This pipeline aligns your FastQ files with BWA-MEM, realigns indels
and calls variants with LoFreq and annotates the resulting vcf file
with SNPeff. The produced ``*genes.txt`` files from multiple samples
can be used as input for ``essential_genes_from_tables.py`` (can be
found in this folder) to predict essential genes.

All runtime variables can be found in ``conf.yaml``

Prerequisites
-------------

Your reference fasta file must match the given SNPeff genomes. Your
genome of choice also has to be in the list of supported locally
available databases, i.e. it might have to be downloaded first.

How to
------

- Run ``essential-genes.py -h`` to get basic usage information.
- Using -v is recommended to get some more information
- If called correctly, jobs will be run on the cluster automatically
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster mode).
- All log files can be found in ``./logs/``
- All output files can be found in ``./out/``




