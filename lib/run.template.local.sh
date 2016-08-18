#!/bin/bash

# This is a fake "submission" to be able to run jobs locally. To run it use
#   bash run.sh
#
# The environment variable EXTRA_SNAKEMAKE_ARGS will be passed down to
# snakemake. This allows for example to execute a dryrun:
#   EXTRA_SNAKEMAKE_ARGS="--dryrun" bash|qsub run.sh
# or alternatively:
#   export EXTRA_SNAKEMAKE_ARGS="--dryrun"
#   bash|qsub run.sh
#
# If the environment variable DEBUG is set the snakemake command will
# be printed but not exectuted
#
# Potentially useful arguments:
# --keep-going : irritating. best to fail immediately
# --notemp : for debug only
# --forceall : for debug only
# --dryrun : just print what would happen


DEBUG=${{DEBUG:-0}}
SNAKEFILE={SNAKEFILE}
LOGDIR="{LOGDIR}";# should be same as defined above
DEFAULT_SNAKEMAKE_ARGS="--rerun-incomplete --timestamp --printshellcmds --stats $LOGDIR/snakemake.stats --configfile conf.yaml --latency-wait 60"
# --rerun-incomplete: see https://groups.google.com/forum/#!topic/snakemake/fbQbnD8yYkQ
# --timestamp: prints timestamps in log
# --printshellcmds: also prints actual commands
# --latency-wait: might help with FS sync problems. also used by broad: https://github.com/broadinstitute/viral-ngs/blob/master/pipes/Broad_LSF/run-pipe.sh


if [ "$ENVIRONMENT" == "BATCH" ]; then
    echo "ERROR: Script is for local mode only" 1>&2
    exit 1
else
    # run locally
    CLUSTER_ARGS=""
    N_ARG="--cores 8"
fi


if [ "$DEBUG" -eq 1 ]; then
    #echo "DEBUG *ENV* $(set | grep ENV)" 1>&2;
    echo "DEBUG \$0=$0" 1>&2;
    echo "DEBUG $SHELL=$SHELL" 1>&2;
    echo "DEBUG python=$(which python)" 1>&2;
    echo "DEBUG snakemake=$(which snakemake)" 1>&2;
    echo "DEBUG EXTRA_SNAKEMAKE_ARGS=$EXTRA_SNAKEMAKE_ARGS" 1>&2
    echo "DEBUG DEFAULT_SNAKEMAKE_ARGS=$DEFAULT_SNAKEMAKE_ARGS" 1>&2
fi


# dotkit setup
source rc/dk_init.rc || exit 1

# snakemake setup
source rc/snakemake_init.rc || exit 1

test -d $LOGDIR || mkdir $LOGDIR


sm_args="-s $SNAKEFILE"
sm_args="$sm_args $N_ARG"
sm_args="$sm_args $DEFAULT_SNAKEMAKE_ARGS"
sm_args="$sm_args $EXTRA_SNAKEMAKE_ARGS"

# warn if we received any args from outside that match used ones
sm_args_tokenized=$(echo "$sm_args" | tr ' ' '\n' | grep '^-' | sort)
dups=$(echo -e "$sm_args_tokenized" | uniq -d)
if [[ $dups ]]; then
    echo "WARNING: duplicated args: $dups" 1>&2
fi

# now okay to add CLUSTER_ARGS (allows repeated -l)
sm_args="$sm_args $CLUSTER_ARGS"

# ANALYSIS_ID created here so that each run gets its own Id
# iso8601ms timestamp as corresponding python function
iso8601ns=$(date --iso-8601=ns | tr ':,' '-.');
iso8601ms=${{iso8601ns:0:26}}
ANALYSIS_ID=$iso8601ms
sm_args="$sm_args --config ANALYSIS_ID=$ANALYSIS_ID"


# mongodb update has to happen here because at this stage we know the
# job has been submitted. at the same time we avoid cases where a job
# stuck in queue will be rerun. but don't update if running in dryrun
# mode
is_dryrun=0
sm_args_tokenized=$(echo "$sm_args" | tr ' ' '\n' | grep '^-' | sort)
for arg in $sm_args_tokenized; do
    if [ $arg == "-n" ] || [ $arg == "--dryrun" ]; then
        is_dryrun=1
        break
    fi
done

if [ $is_dryrun != 1 ]; then
    {LOGGER_CMD}
else
    echo "Skipping MongoDB update (dryrun)"
fi

cmd="snakemake $sm_args >> {MASTERLOG} 2>&1"
if [ $DEBUG -eq 1 ]; then
    echo $cmd
else
    eval $cmd
fi
