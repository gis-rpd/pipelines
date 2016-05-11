cat conf.default.yaml | sed -e "s,\$RPD_GENOMES,$RPD_GENOMES,g" > example.yaml
mkdir mapping 2>/dev/null; touch mapping/first_sample.bam mapping/second_sample.bam
source activate snakemake-3.5.5-g9752cd7-catch-logger-cleanup
snakemake --printshellcmds  --dryrun --configfile example.yaml 
