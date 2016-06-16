#!/bin/bash

# to run this submission script on the cluster use:
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

# UGE options:
# The #$ must be used to specify the grid engine options used by qsub. 
# declare a name for this job to be sample_job
#$ -N @PIPELINE_NAME@.master
# logs
#$ -o @LOGDIR@
# combine stdout/stderr
#$ -j y
# snakemake control job run time: 175h == 1 week
#$ -l h_rt=175:00:00
# memory: shoots up for heavily multiplexed libraries
#$ -l mem_free=16G
# 'parallel env'
#$ -pe OpenMP 1
# run the job in the current working directory (where qsub is called)
#$ -cwd
# keep env so that qsub works
#$ -V
# email address (for abort and kills only, everything else handled by snakemake)
#$ -M @MAILTO@
#$ -m a


DEBUG=0
DEFAULT_SLAVE_Q=@DEFAULT_SLAVE_Q@
SNAKEFILE=@SNAKEFILE@
LOGDIR="@LOGDIR@";# should be same as defined above
DEFAULT_SNAKEMAKE_ARGS="--rerun-incomplete --timestamp --printshellcmds --stats $LOGDIR/snakemake.stats --configfile conf.yaml --latency-wait 60"
# --rerun-incomplete: see https://groups.google.com/forum/#!topic/snakemake/fbQbnD8yYkQ
# --timestamp: prints timestamps in log
# --printshellcmds: also prints actual commands
# --latency-wait: might help with FS sync problems. also used by broad: https://github.com/broadinstitute/viral-ngs/blob/master/pipes/Broad_LSF/run-pipe.sh


if [ "$ENVIRONMENT" == "BATCH" ]; then
    # define qsub options for all jobs spawned by snakemake
    qsub="qsub -pe OpenMP {threads} -l mem_free={cluster.mem} -l h_rt={cluster.time}"
    # log files names: qsub -o|-e: "If path is a directory, the standard error stream of
    qsub="$qsub -V -cwd -e $LOGDIR -o $LOGDIR"
    if [ -n "$SLAVE_Q" ]; then
        qsub="$qsub -q $SLAVE_Q"
    elif [ -n "$DEFAULT_SLAVE_Q" ]; then 
        qsub="$qsub -q $DEFAULT_SLAVE_Q"
    fi
    CLUSTER_ARGS="--cluster-config cluster.yaml --cluster \"$qsub\" --jobname \"@PIPELINE_NAME@.slave.{rulename}.{jobid}.sh\""
    N_ARG="--jobs 100"
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

# ANALYSIS_ID created here so that each run gets its own Id
# iso8601ms timestamp as corresponding python function
iso8601ns=$(date --iso-8601=ns | tr ':,' '-.');
iso8601ms=${iso8601ns:0:26}
ANALYSIS_ID=$iso8601ms
args="$args --config ANALYSIS_ID=$ANALYSIS_ID"

# dotkit setup
source rc/dk_init.rc || exit 1


# snakemake setup
source rc/snakemake_init.rc || exit 1


test -d $LOGDIR || mkdir $LOGDIR



# mongodb update has to happen here because at this stage we know the
# job has been submitted. at the same time we avoid cases where a job
# stuck in queue will be rerun. but don't update if running in dryrun
# mode
is_dryrun=0
args_tokenized=$(echo "$args" | tr ' ' '\n' | grep '^-' | sort)
for arg in $args_tokenized; do
    if [ $arg == "-n" ] || [ $arg == "--dryrun" ]; then
        is_dryrun=1
        break
    fi
done

if [ $is_dryrun != 1 ]; then
    @MONGO_UPDATE_CMD@
else
    echo "Skipping MongoDB update (dryrun)"
fi

eval snakemake $args >@MASTERLOG@ 2>&1

