#!/bin/bash

pipeline=$1
test -z "$pipeline" && exit 1

for based in $RPD_ROOT/elm-logs $RPD_ROOT/elm-logs.testing; do
    d=$based/$pipeline
    echo "Creating $d (if needed) and setting perms as required"
    test -d $d || mkdir $d
    chmod 777 $d
    chmod g+s $d
done