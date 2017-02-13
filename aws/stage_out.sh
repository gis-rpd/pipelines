#!/bin/bash

set -euo pipefail

# Andreas Wilm <wilma@gis.a-star.edu.sg>
# 
# Locking template from http://stackoverflow.com/questions/1715137/what-is-the-best-way-to-ensure-only-one-instance-of-a-bash-script-is-running
#
# original copyright notice for locking template:
## Copyright (C) 2009 Przemyslaw Pawelczyk <przemoc@gmail.com>
##
## This script is licensed under the terms of the MIT license.
## https://opensource.org/licenses/MIT

DEFAULT_BUCKET="s3://rpd-workflows-out/"

LOCKFILE="";# set later depending on input
LOCKFD=99


# PRIVATE
_lock()             { flock -$1 $LOCKFD; }
_no_more_locking()  { test -z "$LOCKFILE" && exit 1; _lock u; _lock xn && rm -f $LOCKFILE; }
_prepare_locking()  { eval "exec $LOCKFD>\"$LOCKFILE\""; trap _no_more_locking EXIT; }


# PUBLIC
exlock_now()        { _lock xn; }  # obtain an exclusive lock immediately or fail
exlock()            { _lock x; }   # obtain an exclusive lock
shlock()            { _lock s; }   # obtain a shared lock
unlock()            { _lock u; }   # drop a lock


usage() { 
    myname=$(basename $0)
    echo "$myname: upload tarball of given directory dir to given S3 bucket" 1>&2
    echo "Usage: $myname [-u | -b s3bucket (default: $DEFAULT_BUCKET)] [-r] [-f] dir" 1>&2
    echo "Options:" 1>&2
    echo " -u unlock : Unlock directory (UNUSED)" 1>&2
    echo " -b bucket : Use this bucket instead of $DEFAULT_BUCKET" 1>&2
    echo " -r        : Remove local copy after upload" 1>&2
    echo " -f        : Force overwrite" 1>&2
    #echo "Example: $myname -b bucket] dir " 1>&2
    exit 1
}


unlock=0
remove=0
force=0
bucket=$DEFAULT_BUCKET
while getopts "b:urf" o; do
  case "${o}" in
        u)
            unlock=1
            ;;
        b)
            bucket=${OPTARG}
            ;;
        r)
            remove=1
            ;;
        f)
            force=1
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ $# != 1 ]; then
    usage
fi

bucket=$(echo $bucket | sed -e "s,/*$,,");# beware the double slash

if [ $unlock -eq 1 ]; then
    echo "FATAL: option unlock not implemented (useful at all?)" 1>&2
    exit 1
fi

wdir=$(readlink -f $1) || exit 1
if [ ! -d $wdir ]; then
    echo "FATAL: Non-existant workflow directory \"$wdir\"" 1>&2
    exit 1
fi
flagfile=logs/snakemake.log
if [ ! -e $wdir/$flagfile ]; then
    echo "FATAL: Don't recognize \"$wdir\" as workflow directory" 1>&2
    exit 1
fi


LOCKFILE=$wdir/$(basename $0).LOCK
#echo "Trying to lock $wdir (using $LOCKFILE)"
_prepare_locking
# avoid running multiple instances of script
if ! exlock_now; then
    echo "FATAL: couldn't aquire lock" 1>&2
    exit 1
fi


pushd $wdir >/dev/null
cd ..
wdirbase=$(basename $wdir)
tarball=${wdirbase}.tgz


# first check if exists
if aws s3 ls $bucket | grep -qw $tarball 2>/dev/null; then
    if [ $force -ne 1 ]; then
	echo "FATAL: refusing to overwrite exising object. Please use --force if needed" 1>&2
	exit 1
    fi
fi

uri=$(echo ${bucket}/$tarball)
#cat<<EOF
tar c --exclude '*/.snakemake/*' $wdirbase | aws s3 cp - $uri
#EOF

popd >/dev/null

if [ $remove -eq 1 ]; then
    # save to remove since we checked above that it does exist and is
    # a real workflow dir
    rm -rf $wdir
fi

#echo "Done"
