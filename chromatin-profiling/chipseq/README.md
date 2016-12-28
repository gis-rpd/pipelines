# ChIPseq

## Summary

This pipeline calls peaks in ChIP-Seq data with
[MACS2](https://github.com/taoliu/MACS)
and [DFilter](http://collaborations.gis.a-star.edu.sg/~cmb6/kumarv1/dfilter/) and performs motif discovery with [MEME-ChIP](http://meme-suite.org/).


The following steps are performed:

- Read mapping (with BWA aln by default; see `cfg/references.yaml` for default references and also refer to option `--references-cfg`)
- Filtering of duplicated, unmapped reads and reads with bad mapping quality (Q20)
- Peak calling with MACS2 and DFilter with control and treatment samples (settings depends on the used peak type, see `-t`)
- Extraction of sequences around extended peak regions followed by motif discovery with MEME-ChIP

## Output

Processed BAM files (`*.bwa-aln-nsrt.bam`) for control and treatment samples can be found in the correspondingly named subfolders in `./out/`.

Peak calling results, motif discovery results and mapping stats can be found in the `./out/treatment` subfolders. The most important are
- `treatment_peaks.xls`: Called peaks and peaks coordinates (MACS2 only)
- `treatment.Peaks`: Called peaks and peaks coordinates (DFilter only)
- `treatment_summits.bed`: Peak summit locations for every peak
- `treatment_control_lambda.bw`: Control tag density profile
- `treatment_treat_pileup.bw`: Treatment tag density profile
- `treatment_filtered_treatment.wig`: Background smoothened treatment tag density profile (DFilter only)
- `treatment-memechip/index.html`: Motif discovery results
- `treatment.bwa-aln-nsrt.bamstats/stats.txt`: Mapping stats


