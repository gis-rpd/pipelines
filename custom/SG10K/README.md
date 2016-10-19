# SG10K

## Summary

This workflow is for pre-processing of SG10K samples (shallow human WGS) which are 
meant to be further processed with gotcloud. The following steps are
performed:

- Alignment of reads with BWA-MEM against hs37d5 from the gotcloud
  bundle
- Duplicate marking with samblaster
- Base-quality recalibration with bamutils' recab. See
  `{sample}.bwamem.fixmate.mdups.srt.recal.bam`
- Creation of simple mapping statistics (bamstats, idxstats). See
  `{sample}.bwamem.fixmate.mdups.srt.recal.bamstats`
- Contamination check with verifyBamID (Chinese, Indian and Malay
  vcf's). See `{sample}.bwamem.fixmate.mdups.srt.recal.{race}.selfSM`

These and following steps are prone to change and should hence not considered as production version!
