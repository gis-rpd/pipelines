# freebayes

## Summary

This pipeline calls (germline) variants with Freebayes. It's main
output files are a recalibrated BAM and a VCF file (per sample).

See `cfg/references.yaml` for references used by default (also refer
to option `--references-cfg`)

In order to speed the analysis up and avoid unnecessary IO operations,
Freebayes is run on the entire BAM file even when given a BED-file
(variants in regions of interest are filtered later). If you are only
interested in a very small region in an otherwise fully sequenced
sample, the analysis will therefore appear slow.
    
## Output

- BAM file: `{sample}.bwamem.dedup.bam`
- BAM stats: `{sample}.bwamem.dedup.bamstat`
- Variant-quality filtered calls: `{bam}.freebayes.hfilter.vcf.gz`
- As above but with annotation: `{bam}.freebayes.hfilter.snpeff.vcf.gz`


## References

- [Freebayes Homepage](https://github.com/ekg/freebayes/wiki)
- [Garrison E, Marth G. Haplotype-based variant detection from short-read sequencing. arXiv:1207.3907, 2012](http://arxiv.org/abs/1207.3907)
