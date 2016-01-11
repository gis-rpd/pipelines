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
## specify your email address
#$ -M wilma@gis.a-star.edu.sg
## mail is sent to you when the job starts and when it terminates or aborts
#$ -m bea
## run the job in the current working directory (where qsub is called)
#$ -cwd


# Within snakemake we're not using a login shell. Hence, it's unaware
# of some needed settings, e.g. lmod and UGE which are set below. Any
# snakemake spawned jobs will be informed about them via qsub -V (see
# below)

# UGE setup (as in /etc/profile)
#
echo "Setting up UGE"
export SGE_ROOT=/opt/uge-8.1.7p3
export SGE_CELL=aquila_cell
source $SGE_ROOT/$SGE_CELL/common/settings.sh

# lmod
#
echo "Setting up lmod"
lmod=/mnt/software/stow/Lmod-6.0.24/lmod/6.0.24/
# only needed of BASH_ENV set according to lmod6 installation instructions
source $lmod/init/bash
module purge
module use /mnt/projects/rpd/apps/modules

# load fixed snakemake version
#
echo "Activating snakemake"
export PATH=/mnt/projects/rpd/apps/miniconda3/bin/:$PATH; 
source activate snakemake-3.5.4;

# define qsub options for all jobs spawned by snakemake
qsub="qsub -pe OpenMP {threads} -l mem_free=10G -l h_rt=72:00:00 -j y -V -b y -cwd"

snakemake --configfile conf.yaml -j 16 -c "$qsub"
