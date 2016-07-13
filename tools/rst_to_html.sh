#!/bin/bash

BASE_DIR=$(readlink -f $(dirname $(readlink -f $0))/..)
#echo "DEBUG: BASE_DIR=$BASE_DIR" 1>&2

flagfile=$BASE_DIR/bcl2fastq/README.rst
if [ ! -e $flagfile ]; then
    echo "FATAL: Looks like I'm in the wrong dir (couldn't find $flagfile)" 1>&2
    exit 1
fi
which rst2html.py >/dev/null || exit 1

for rst in $(find $BASE_DIR -maxdepth 2 -name README.rst); do
    html=${rst%.rst}.html
    rst2html.py $rst > $html && echo "Created $html"
    
done

