# bcl2fastq

## Summary

- Runs bcl2fastq on Illumina sequencer output with settings inferred from ELM (if not overwritten manually)
- MUXes are processed in parallel and each has it's own folder (i.e. `./out/Project_<MUX>`)
- Each MUX component library has its own sub-folder (e.g. `./out/Project_<MUX>/Sample_<lib>`)
- In addition, FastQC is run on each fastq file


## Warning

End-users will not want to use this pipeline!

The directory contains auxiliary scripts used for production
operations only.
