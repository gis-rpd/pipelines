# essential-genes

## Summary

This pipeline predicts essential genes from non-clonal bacterial samples.

It aligns your FastQ files with BWA-MEM, realigns indels and calls
variants with LoFreq and annotates the resulting vcf-file with SNPeff.

The `*genes.txt` files from multiple samples can be used as input for
`essential_genes_from_tables.py` (also found in this folder) to
predict essential genes. Please contact Andreas Wilm
<<mailto:wilma@gis.a-star.edu.sg>> or Niranjan Nagarajan
<<mailto:nagarajann@gis.a-star.edu.sg>> regarding details for the
latter.


## Prerequisites

Your reference fasta file must match the given SNPeff genomes. Your
genome of choice also has to be in the list of supported locally
available databases, i.e. it might have to be downloaded first (please
contact us to do so)

For admins: The command to use is `java -jar $SNPEFFDIR/snpEff.jar download -c $SNPEFFDIR/snpEff.config -v $SPECIES`
