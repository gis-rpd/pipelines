#!/usr/bin/env python3
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

with open("conf.yaml") as fh:
    data = load(fh, Loader=Loader)

for k, v in data.items():
    print(k, v)
    
