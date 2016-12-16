# ChIPseq

## Summary

This pipeline calling peaks of ChIP-Seq data with peak caller programs MACS2 and DFilter.
MACS version macs2 2.1.0.20150731; see [paper] (https://genomebiology.biomedcentral.com/articles/10.1186/gb-2008-9-9-r137) and [homepage] (https://github.com/taoliu/MACS)
DFilter version 1.6; see [paper] (http://www.nature.com/nbt/journal/v31/n7/full/nbt.2596.html)
and [homepage] (http://collaborations.gis.a-star.edu.sg/~cmb6/kumarv1/dfilter/tutorial.html#parameters), [faq] (http://collaborations.gis.a-star.edu.sg/~cmb6/kumarv1/dfilter/dfilter-FAQs.html)
The motif discovery by meme prog. see [paper] (http://nar.oxfordjournals.org/content/37/suppl_2/W202.full) and [homepage] (http://meme-suite.org/)

The following steps are performed:

- Read mapping (see `cfg/references.yaml` for references used by default  and also refer to  option `--references-cfg`)
- Filtering duplicated reads, unmapped reads and reads with bad mapping quality (-q 20) with samtools
- Peak calling with MACS and DFilter with control and input samples (see `cfg/params.yaml` for parameters used by default  and also refer to  option ` --modules-cfg`)
- Generating visualization files "BigWig" and extract the sequences of extended peak summit region followed by motif discovery with meme
- Annotating the peaks with nearest genes and genome wide region assignment

## Output

- Mapped and processed BAM files for control and treatment in the correspondly named subfolders
- Peak calling results, motif discovery results and mapping stats can be found in the treatment subfolders. The most important are
    - `treatment_peaks.xls`: Information about the called peaks and peaks coordinates (macs2 only)
    - `treatment.Peaks`: Information about the called peaks and peaks coordinates (dfilter only)
    - `treatment_summits.bed`: Bed format of the peak summits locations for every peak
    - `treatment_control_lambda.bw`: Control tag density profile to Visualize in ucsc/igv
    - `treatment_treat_pileup.bw`: Treatment tag density profile to Visualize in ucsc/igv
    - `treatment_filtered_treatment.wig`: Background smoothened treatment tag density profile (dfilter only)
    - `index.html and meme.html`: Discovered motif results
    - `stats.txt`: Mapping rate stats

