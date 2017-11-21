# freebayes


## Summary

This pipeline calls variants with Freebayes. It's main output files are a
recalibrated BAM and a VCF file (per sample).

See `cfg/references.yaml` for references used by default (also refer
to option `--references-cfg`)


## Output

- BAM files:  `{sample}.bwamem.dedup.bqsr.bam` or `{sample}.bwamem.dedup.bam`, depending on whether BQSR was run or not (see above)
- Variant-quality filtering calls: `{bam}.hfilter.vcf.gz` (with annotation: `{bam}.gt.{vartype}_hfilter.snpeff.vcf.gz`)


## References


- [Freebayes Homepage](https://github.com/ekg/freebayes/wiki)
