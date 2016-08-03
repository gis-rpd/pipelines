#!/usr/bin/env python3
from collections import OrderedDict
from gzip import open
from os import path
from sqlite3 import connect
from sys import argv

# man accounting | grep '^   [A-Za-z0-9]'
FIELDS = ['qname', 'hostname', 'group', 'owner', 'job_name',
          'job_number', 'account', 'priority','submission_time',
          'start_time', 'end_time', 'failed', 'exit_status',
          'ru_wallclock', 'project', 'department', 'granted_pe',
          'slots', 'task_number', 'cpu', 'mem', 'io', 'category',
          'iow', 'pe_taskid', 'maxvmem', 'arid', 'ar_submission_time',
          'job_class']

acct = argv[1]
assert path.exists(acct)
try:
	jid = argv[2]
except:
	jid = None


if (not path.isfile("aws.db")):
	db = connect("aws.db")
	db.close()
	db.execute('''CREATE TABLE accounting(
	              JOB_NUMBER   INT      PRIMARY KEY,
	              JOB_NAME     TEXT     NOT NULL,
	              SLOTS        INT      NOT NULL,
	              H_VMEM       TEXT		NOT NULL,
	              MAXVMEM      DECIMAL  NOT NULL,
	              RU_WALLCLOCK INT      NOT NULL
		     );''')
	print ("CREATED DATABASE: aws.db")
else:
	print ("FOUND DATABASE: aws.db")


with open(acct) as fh:
    for line in fh:
        l = line.decode().rstrip().split(':')
        if l[0].startswith('#'):
            continue
        d = OrderedDict(zip(FIELDS, l))
        if jid:
            if d['job_number']==jid:
                for k, v in d.items():
                    print(k, v)
        elif jid:
            print(d)
