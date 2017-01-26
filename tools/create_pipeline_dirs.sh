#!/bin/bash

pipelines=$@
test -z "$pipelines" && exit 1

# elm logging dirs
#
for m in rpd/testing rpd/production; do
  module load $m
  for p in $pipelines; do
    d=$RPD_ELMLOGDIR/$p
#cat<<EOF
    test -d $d || mkdir -p $d 2>/dev/null
    chmod 777 $d
    chmod g+s $d
#EOF
  done
done

# downstream dirs
#
for outdir in $(grep -A2 downstream_outdir_base etc/site.yaml  | awk '/(devel|production):/ {print $NF}'); do
      for p in $pipelines; do
	  d=$outdir/$p
	  echo "Creating $d (if needed) and setting perms as required"
	  test -d $d || mkdir -p $d 2>/dev/null
	  chmod 775 $d
	  chmod g+s $d
      done
done
