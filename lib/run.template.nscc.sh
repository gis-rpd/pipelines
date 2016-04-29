#!/bin/bash

# to run this submission script on aquila use:
#   qsub run.sh
# or to run locally use
#   bash run.sh
# for reruns on aquila use:
#   qsub run.sh >> log/submission.log
#
# The environment variable EXTRA_SNAKEMAKE_ARGS will be passed down to
# snakemake. This allows for example to execute a dryrun:
#   EXTRA_SNAKEMAKE_ARGS="--dryrun" bash|qsub run.sh
# or alternatively:
#   export EXTRA_SNAKEMAKE_ARGS="--dryrun"
#   bash|qsub run.sh
# The environment variable SLAVE_Q will be used to specify a queue for
# the "worker processes" (otherwise DEFAULT_SLAVE_Q set here will be used
# or scheduler decides if empty)
#
#
# Potentially useful arguments:
# --keep-going : irritating. best to fail immediately
# --notemp : for debug only
# --forceall : for debug only
# --dryrun : just print what would happen

# PBS Pro options:
# The #PBS must be used to specify PBS Pro options
# declare a name for this job to be sample_job
#PBS -N @PIPELINE_NAME@.master
# logs
#PBS -o @MASTERLOG@
# combine stdout/stderr
#PBS -j oe
# snakemake control job run time: 175h == 1 week
#PBS -l walltime=175:00:00
# memory
#PBS -l select=1:mem=1g
# cpu
#PBS -l select=1:ncpus=1
# keep env so that qsub works
#PBS -V
# Equivalent for SGE's -cwd doesn't exist in PBS Pro. See below for workaround
# Email address (for abort and kills only, everything else handled by snakemake)
#PBS -M @MAILTO@
#PBS -m a


DEBUG=0
DEFAULT_SLAVE_Q=@DEFAULT_SLAVE_Q@
SNAKEFILE=@SNAKEFILE@

DEFAULT_SNAKEMAKE_ARGS="--rerun-incomplete --timestamp --printshellcmds --stats snakemake.stats --configfile conf.yaml --latency-wait 60"
# --rerun-incomplete: see https://groups.google.com/forum/#!topic/snakemake/fbQbnD8yYkQ
# --timestamp: prints timestamps in log
# --printshellcmds: also prints actual commands
# --latency-wait: might help with FS sync problems. also used by broad: https://github.com/broadinstitute/viral-ngs/blob/master/pipes/Broad_LSF/run-pipe.sh

#export SGE_ROOT=/opt/uge-8.1.7p3
#export SGE_CELL=aquila_cell
#source $SGE_ROOT/$SGE_CELL/common/settings.sh

LOGDIR="@LOGDIR@";# should be same as defined above for UGE

if [ "$ENVIRONMENT" == "BATCH" ]; then
    # define qsub options for all jobs spawned by snakemake
    qsub="qsub -l select=1:ncpus={threads} -l select=1:mem={cluster.mem} -l walltime={cluster.time}"
    # log files names: qsub -o|-e: "If path is a directory, the standard error stream of
    qsub="$qsub -V -e $LOGDIR -o $LOGDIR"
    # PBS: cwd (workaround for missing SGE option "-cwd")
    cd $PBS_O_WORKDIR
    if [ -n "$SLAVE_Q" ]; then
        qsub="$qsub -q $SLAVE_Q"
    elif [ -n "$DEFAULT_SLAVE_Q" ]; then 
        qsub="$qsub -q $DEFAULT_SLAVE_Q"
    fi
    CLUSTER_ARGS="--cluster-config cluster.yaml --cluster \"$qsub\" --jobname \"@PIPELINE_NAME@.slave.{rulename}.{jobid}.sh\""
    N_ARG="--jobs 6"
else
    # run locally
    CLUSTER_ARGS=""
    N_ARG="--cores 8"
fi

if [ "$DEBUG" -eq 1 ]; then
    echo "DEBUG ENVIRONMENT=$ENVIRONMENT" 1>&2;
    #echo "DEBUG *ENV* $(set | grep ENV)" 1>&2;
    echo "DEBUG \$0=$0" 1>&2;
    echo "DEBUG $SHELL=$SHELL" 1>&2;
    echo "DEBUG python=$(which python)" 1>&2;
    echo "DEBUG snakemake=$(which snakemake)" 1>&2;
    echo "DEBUG CLUSTER_ARGS=$CLUSTER_ARGS" 1>&2
    echo "DEBUG EXTRA_SNAKEMAKE_ARGS=$EXTRA_SNAKEMAKE_ARGS" 1>&2
    echo "DEBUG DEFAULT_SNAKEMAKE_ARGS=$DEFAULT_SNAKEMAKE_ARGS" 1>&2
fi


args="-s $SNAKEFILE"
args="$args $N_ARG"
args="$args $DEFAULT_SNAKEMAKE_ARGS"
args="$args $EXTRA_SNAKEMAKE_ARGS"

# warn if we received any args from outside that match used ones
args_tokenized=$(echo "$args" | tr ' ' '\n' | grep '^-' | sort)
dups=$(echo -e "$args_tokenized" | uniq -d)
if [[ $dups ]]; then
    echo "WARNING: duplicated args: $dups" 1>&2
fi

# now okay to add CLUSTER_ARGS (allows repeated -l)
args="$args $CLUSTER_ARGS"


# dotkit setup
source dk_init.rc || exit 1


# snakemake setup
source snakemake_init.rc || exit 1


test -d $LOGDIR || mkdir $LOGDIR


#cat<<EOF
eval snakemake $args
#EOF


