#!/usr/bin/env python3
from argparse import ArgumentParser
from gzip import open
from os import path
from sqlite3 import connect
from sys import argv

FIELDS = ['qname', 'hostname', 'group_id', 'owner', 'job_name',
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


#instance = ArgumentParser(description=__doc__)
#instance.add_argument("-j", "--jobNo", nargs="*", help="filter records by jobNo of jobs")
#instance.add_argument("-o", "--owner", nargs="*", help="filter records by owner of jobs")
#args = instance.parse_args()


if (not path.isfile("aws.db")):
	db = connect("aws.db")
	db.execute('''CREATE TABLE accounting(
	qname			TEXT		NOT NULL,
	hostname		TEXT		NOT NULL,
	group_id		TEXT		NOT NULL,
	owner			TEXT		NOT NULL,
	job_name		TEXT		NOT NULL,
	job_number		INTEGER		NOT NULL,
	account			TEXT		NOT NULL,
	priority		INTEGER		NOT NULL,
	submission_time		INTEGER		NOT NULL,
	start_time		INTEGER		NOT NULL,
	end_time		INTEGER		NOT NULL,
	failed			INTEGER		NOT NULL,
	exit_status		INTEGER		NOT NULL,
	ru_wallclock		INTEGER		NOT NULL,
	project			REAL		NOT NULL,
	department		REAL		NOT NULL,
	granted_pe		REAL		NOT NULL,
	slots			INTEGER		NOT NULL,
	task_number		INTEGER		NOT NULL,
	cpu			INTEGER		NOT NULL,
	mem			INTEGER		NOT NULL,
	io			INTEGER		NOT NULL,
	category		TEXT		NOT NULL,
	iow			INTEGER		NOT NULL,
	pe_taskid		REAL		NOT NULL,
	maxvmem			INTEGER		NOT NULL,
	arid			INTEGER		NOT NULL,
	ar_submission_time	INTEGER		NOT NULL,
	job_class		TEXT		NOT NULL
);''')
	db.close()
	print ("CREATED DATABASE: aws.db")
else:
	print ("FOUND DATABASE: aws.db")


with open(acct) as fh:
	for line in fh:
		l = line.decode().rstrip().split(':')
		if l[0].startswith('#'):
			continue

		a = ''
		for f in FIELDS:
			a = (a + ", '" + f + "'")

		b = ''
		for j in l[:29]:
			b = (b + ", '" + j + "'")

#		print ("INSERT INTO accounting (" + a[2:] + ") VALUES (" + b[2:] + ");")
		db = connect("aws.db")
		db.execute("INSERT INTO accounting (" + a[2:] + ") VALUES (" + b[2:] + ");")
		db.commit()
		db.close()
#		d = OrderedDict(zip(FIELDS, l))

#		if jid:
#			if d['job_number'] == jid:
#				for k, v in d.items():
#					print (k, v)
