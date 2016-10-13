# BWA-MEM

## Summary

This is a plain BWA-MEM mapping pipeline that maps reads to a given reference. Duplicate
reads are marked by default, if not requested otherwise.

- The final BAM file is called `{sample}.bwamem.dedup.bam` (without `dedup` if PCR duplicate removal was switched off)
- Mapping stats can be found in a correspondingly named `bamstats` folder
