# vipr3


## Summary

ViPR assembles your viral NGS reads and analyses low frequency
variants (quasispecies) in your data.  ViPR3 is losely based on its
predecessors: the original [ViPR](https://github.com/CSB5/vipr) and
[ViPR2](https://github.com/CSB5/ViPR2).

In a first step reads are quality trimmed and adapters removed
with Skewer. Reads are then assembled in two different ways:
- With Spades after digital
  normalization with bbnorm (part of BBTools)
- With Tadpole (part of BBTools)

Resulting contigs are QCed (visualization only) with Mummer and then
joined and gap-filled (if needed) with the user-provided
reference. Trimmed reads will then be mapped against the two
assemblies and also against the user-provided reference with
BWA-MEM. Finally variants are called with LoFreq. A plot showing
coverage and SNP allele frequency is produced for all three mappings.


## Output

- Reads directory: `{sample}/reads/`
- Cleaned, joined reads used for mapping: `{sample}/reads/R[12].fastq.gz`
- Assembly directory: `{sample}/assembly/{method}`
- Mapping directory: `{sample}/mapping/{method}`
- Contig visualization: `{sample}/assembly/{method}/scaffolds.fasta_QC/nucmer.coords.png`
- Gap filled assembly: `{sample}/assembly/{method}/scaffolds.fasta`
- Alignment: `{sample}/mapping/{method}/{sample}.bwamem.lofreq.bam`
- Coverage: `{sample}/mapping/{method}/{sample}.bwamem.lofreq.cov.gz`
- Variants: `{sample}/mapping/{method}/{sample}.bwamem.lofreq.vcf.gz`
- Visualization of coverage and SNP allele frequency: `{sample}/mapping/{method}/{sample}.bwamem.lofreq.plot.png`

`method` is either `tadpole` or `spades` (and also `input-ref` for
mapping). The mapping folders contain the corresponding reference as
`ref.fa` symlink.

## References

- LoFreq: [publication](https://www.ncbi.nlm.nih.gov/pubmed/23066108) and [website](http://csb5.github.io/lofreq/)
- Spades: [publication](https://www.ncbi.nlm.nih.gov/pubmed/22506599) and [website](http://cab.spbu.ru/software/spades/)
- BBtools: [website](http://jgi.doe.gov/data-and-tools/bbtools/)
- Skewer: [publication](https://www.ncbi.nlm.nih.gov/pubmed/24925680) and [website](https://github.com/relipmoc/skewer)
- Mummer: [publication](https://www.ncbi.nlm.nih.gov/pubmed/14759262) and [website](http://mummer.sourceforge.net/)
