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
## keep env so that qsub works. otherwise see settings below
#$ -V


#export SGE_ROOT=/opt/uge-8.1.7p3
#export SGE_CELL=aquila_cell
#source $SGE_ROOT/$SGE_CELL/common/settings.sh


eval `@INIT@`


# load snakemake
#
echo "Activating snakemake"
use miniconda-3
#export PATH=/mnt/projects/rpd/apps/miniconda3/bin/:$PATH
source activate snakemake-3.5.4;


# define qsub options for all jobs spawned by snakemake
#
# log files names: qsub -o|-e: "If path is a directory, the standard error stream of
# the job will be put in this directory under the default filename."
# see https://groups.google.com/forum/#!topic/snakemake/5BRHiWUbIaA for alternatives
#
clusterlogdir="./logs/"
test -d $clusterlogdir || mkdir $clusterlogdir
qsub="qsub -pe OpenMP {threads} -l mem_free={cluster.mem} -l h_rt={cluster.time} -V -cwd -e $clusterlogdir -o $clusterlogdir"
cluster_args="--cluster-config cluster.yaml --cluster \"$qsub\""
# set cluster_args to "" for local runs


keepgoing="--keep-going";# irritating. fail immediately
keepgoing=""
notemp="--notemp";# for debug only
notemp=""
force="--forceall";#for debug only
force=""
dryrun="--dryrun"
dryrun=""
# for --rerun-incomplete see https://groups.google.com/forum/#!topic/snakemake/fbQbnD8yYkQ

eval snakemake --configfile conf.yaml --stats snakemake.stats -s @SNAKEFILE@ \
          --rerun-incomplete --timestamp --printshellcmds \
          -j 10 $cluster_args $keepgoing $notemp $force $dryrun \
