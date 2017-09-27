# atacseq

## Summary

This pipeline calls signals of single-cell ATAC-seq data using MACS2.

The following steps are performed (modelled after
[Buenrostro et al., (2015)](https://www.ncbi.nlm.nih.gov/pubmed/26083756)):
- The input reads (assumed to be adapter trimmed) are mapped with
  Bowtie2 (fragment length can be set with `--fragment-length`).
- Discordant and unaligned reads are immediately dropped
- For default references see option `--references-cfg` and `cfg/references.yaml`
- Duplicates are marked with Sambamba
- Duplicated reads as well as those with low mapping quality (Q30) and
  reads not mapping against autosomes (see `cfg/references.yaml`) are
  removed
- Peaks are called with MACS2 (broad and narrow). Peaks summits are
  converted to bed files (extended with `--peak-ext-bp`)-
- MACS2 is run with `--nomodel -f BAMPE --nolambda --call-summits` for
  PE data and `--nomodel --shift -100 --extsize 200` for SE data (see
  `--shift` and `--extsize` for SE specific MACS2 options)
- 
- Modelled after doi:10.1038/nature14590
- Alignment with Bowtie
- Filtering
- Calls narrow and broad peaks with MACS

## Output

- Results appear per sample in `out/{sample}/`
- Filtered BAM file: `out/{sample}/{sample}.bowtie2.dedup.flt.bam`
- Mapping stats are named as bamfiles with `stats` attached
- Called peaks and their coordinates `out/{sample/macs2-{peaktype}/{sample}_peaks.xls`
- Extended peak summit location `out/{sample}/macs2-{peaktype}/{sample}_summits.bed`
- Tag density profile out/{sample}/macs2-{peaktype}/{sample}_treat_pileup.bw

where `{peaktype}` is 'narrow' or 'broad'

## References

- [Bowtie2](http://bowtie-bio.sf.net/bowtie2)
- [MACS2](https://github.com/taoliu/MACS)
