# lacer-lofreq

This pipeline calls somatic variants with [LoFreq](http://csb5.github.io/lofreq/).


The following steps are performed:

- Read mapping (see `cfg/references.yaml` for references used by default  and also refer to  option `--references-cfg`)
- Duplicate marking with samblaster (if not instructed otherwise)
- Realignment with `lofreq viterbi`
- Base quality recalibration with `Lacer` (Swaine Chen
  <<mailto:slchen@gis.a-star.edu.sg>>), unless sequencing type is  "targeted"
- Calling of somatic variants (SNVs and indels) with [LoFreq Somatic](http://csb5.github.io/lofreq/)


## Summary


This pipeline maps your reads to a given reference, marks duplicate
reads (if not instructed otherwise), realigns your reads with `lofreq
viterbi`, recalibrates base qualities with Lacer (author:
`Swaine Chen <mailto:slchen@gis.a-star.edu.sg>`_) and calls SNVs and indels with `LoFreq
<http://csb5.github.io/lofreq/>`_.


## Output

- Realigned and recalibrated BAM file:
  `{sample}.bwamem.lofreq.dedup.lacer.bam` (`dedup` will be missing if
  mark duplicates was switched off)
- Variants (`snps` or `indels`): BAM name + `.{vartype}.vcf.gz`
- Variants annotated with SnpEff end in `.{vartype}.snpeff.vcf.gz`


