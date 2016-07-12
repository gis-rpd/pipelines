Description
-----------

This pipeline aligns your FastQ files with BWA-MEM, realigns indels
and calls variants with LoFreq and annotates the resulting vcf file
with SNPeff. The produced ``*genes.txt`` files from multiple samples
can be used as input for ``essential_genes_from_tables.py`` (can be
found in this folder) to predict essential genes.


Prerequisites
-------------

Your reference fasta file must match the given SNPeff genomes. Your
genome of choice also has to be in the list of supported locally
available databases, i.e. it might have to be downloaded first.

How to
------

- Run ``essential-genes.py -h`` to get basic usage information.
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





