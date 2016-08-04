#!/bin/bash

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))

toaddr() {
    if [ $(whoami) == 'userrig' ]; then
        echo "rpd@gis.a-star.edu.sg";
    else
        echo "$(whoami)@gis.a-star.edu.sg";
    fi
}

usage() {
    echo "$MYNAME: run all pipeline tests"
    echo " -d: Run dry-run tests"
    echo " -r: Run real-run tests"
}

skip_dry_runs=1
skip_real_runs=1
while getopts "dr" opt; do
    case $opt in
        d)
            skip_dry_runs=0
            ;;
        r)
            skip_real_runs=0
            ;;
        \?)
            usage
            exit 1
            ;;
    esac
done

args=""
if [ $skip_dry_runs -ne 1 ]; then
    args="$args -d"
fi
if [ $skip_real_runs -ne 1 ]; then
    args="$args -r"
fi
#echo "DEBUG args=$args" 1>&2

cd $(dirname $0)
commit=$(git describe --always --dirty)

for sh in $(find * -maxdepth 3 -mindepth 1 -name tests.sh); do
    echo "------------------------------------------------------------"
    echo "Running $sh"
    echo "------------------------------------------------------------"
    bash $sh $args
    if [ $? -ne 0 ]; then
        echo "ERROR: Tests failed"
    else
        echo "OK: Tests passed"
    fi
    echo "------------------------------------------------------------"
    echo "Running static code checks in $(dirname $sh)"
    echo "------------------------------------------------------------"
    # only warn
    set +e
    # ignore essential_genes_from_tables.py (python2)
    for f in $(find $(dirname $sh) -maxdepth 1 -name \*py -type f | grep -v flymake | grep -v essential_genes_from_tables.py); do
        echo "Checking $f"
        PYTHONPATH=$(dirname $MYNAME)/lib pylint -j 2 -E --rcfile pylintrc $f
    done
    set -e
    echo "Done"
    echo
done

echo "------------------------------------------------------------"
echo "Running static code checks with pylint in lib"
echo "------------------------------------------------------------"
set +e
for f in $(ls ./lib/*py); do
    echo "Checking $f"
    PYTHONPATH=$(dirname $MYNAME)/lib pylint -j 2 -E --rcfile pylintrc $f
done
echo "Done"
set -e   


echo
echo "*** All tests completed/started"

