#!/usr/bin/env python3
import sys
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

conffile = sys.argv[1]
with open(conffile) as fh:
    data = load(fh, Loader=Loader)

if isinstance(data, dict):
    print("dict")
    for k, v in data.items():
        print(k, v)
else:
    print("list")
    for v in data:
        print(type(v), v)
print("\nOK")
