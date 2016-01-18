#!/bin/bash

# submit with: qsub run.qsub.sh
#
# The #$ must be used to specify the grid engine options used by qsub. 

# UGE options:
## declare a name for this job to be sample_job
#$ -N snakemake.sg10k
## logs
#$ -o snakemake.sg10k.log
## snakemake control job run time
#$ -l h_rt=72:00:00
# memory
#$ -l mem_free=500M
## 'parallel env'
#$ -pe OpenMP 1
## standard error stream of the job is merged into the standard output stream: #$ -j y
## specify your email address: otherwise no email send
#$ -M wilma@gis.a-star.edu.sg
## mail is sent to you when the job starts and when it terminates or aborts
#$ -m bea
## run the job in the current working directory (where qsub is called)
#$ -cwd


source load_env.sh


# define qsub options for all jobs spawned by snakemake
#
# log files names: qsub -o|-e: "If path is a directory, the standard error stream of
# the job will be put in this directory under the default filename."
# see https://groups.google.com/forum/#!topic/snakemake/5BRHiWUbIaA for alternatives
#
clusterlogdir="./clusterlogs/"
test -d $clusterlogdir || mkdir $clusterlogdir
qsub="qsub -pe OpenMP {threads} -l mem_free={cluster.mem} -l h_rt={cluster.time} -V -cwd -e $clusterlogdir -o $clusterlogdir"

# FIXME consider using DRMAA
# FIXME left over jobs when head job was killed. fixed with use of drmaa?
DEVEL=0
if [ "$DEVEL" -eq 1 ]; then
    keepgoing=""
    notemp="--notemp"
    force="--forceall"
else
    keepgoing="--keep-going"
    notemp=""
    force=""
fi

snakemake --cluster-config cluster.yaml \
          --configfile conf.yaml \
          --stats snakemake.stats \
          -j 10 \
          --cluster "$qsub" \
          --rerun-incomplete --timestamp $keepgoing $notemp $force
