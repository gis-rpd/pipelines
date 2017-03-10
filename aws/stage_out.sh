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

S3_PREFIX="s3://rpd-workflows-out/"

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


log() {
    logger -s -t $(basename $0) "$@"
}


usage() { 
    myname=$(basename $0)
    echo "$myname: upload tarball of given directory dir to S3" 1>&2
    echo "Usage: $myname [-u | -p s3-prefix (default: $S3_PREFIX)] [-r] [-f] dir" 1>&2
    echo "Options:" 1>&2
    echo " -u unlock : Unlock directory" 1>&2
    echo " -p bucket : Use this prefix instead of the default ($S3_PREFIX)" 1>&2
    echo " -r        : Remove local copy after upload" 1>&2
    echo " -f        : Force overwrite" 1>&2
    #echo "Example: $myname -b bucket] dir " 1>&2
    exit 1
}


unlock_please=0
remove=0
force=0
s3prefix=$S3_PREFIX
while getopts "p:urf" o; do
  case "${o}" in
        p)
            s3prefix=${OPTARG}
            ;;
        u)
            unlock_please=1
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

s3prefix=$(echo $s3prefix | sed -e "s,/*$,,");# beware the double slash

if [ $# != 1 ]; then
    usage
fi

wdir=$(readlink -f $1) || exit 1
if [ ! -d $wdir ]; then
    log "FATAL: Non-existant workflow directory \"$wdir\""
    exit 1
fi

flagfile=logs/snakemake.log
if [ ! -e $wdir/$flagfile ]; then
    log "FATAL: Don't recognize \"$wdir\" as workflow directory"
    exit 1
fi

LOCKFILE=$wdir/$(basename $0).LOCK

if [ $unlock_please -eq 1 ]; then
    # is this the correct way of doing it?
    test -f $LOCKFILE && rm -f $LOCKFILE
    exit 0
fi


#echo "Trying to lock $wdir (using $LOCKFILE)"
_prepare_locking
# avoid running multiple instances of script
if ! exlock_now; then
    log "FATAL: couldn't aquire lock $LOCKFILE"
    exit 1
fi

pushd $wdir >/dev/null
cd ..
wdirbase=$(basename $wdir)
tarball=${wdirbase}.tar
uri=$(echo ${s3prefix}/$tarball)

# first check if exists
# careful: object acts as prefix on s3 and might list a lot of other stuff
if aws s3 ls $uri >/dev/null; then
    if [ $force -ne 1 ]; then
	log "FATAL: refusing to overwrite exising object. Please use --force if needed"
	exit 1
    fi
fi


# we need a tarball because we might have symlinks which are not supported in s3
# streaming tar is a nice idea, but can hang in pratice. So let's create a copy first
# tar c --exclude '*/.snakemake/*' $wdirbase | aws s3 cp - $uri

tar cf $tarball --exclude '*/.snakemake/*' $wdirbase
if [ $remove -eq 1 ]; then
    # save to remove since we checked above that it does exist and is
    # a real workflow dir
    rm -rf $wdir
fi
aws s3 cp $tarball $uri
rm $tarball

popd >/dev/null

unlock

#echo "Done"
