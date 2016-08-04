#!/usr/bin/env python3
from argparse import ArgumentParser
from collections import OrderedDict
from gzip import open
from os import path, remove
from sqlite3 import connect
from sys import argv

FIELDS = ['qname', 'hostname', 'owner', 'job_name', 'job_number', 'submission_time',
          'start_time', 'end_time', 'failed', 'exit_status', 'ru_wallclock', 'io', 'category', 'maxvmem',
          'h_rt', 'h_vmem', 'mem_free', 'openmp']

#acct = argv[1]
#assert path.exists(acct)
#try:
#	jid = argv[2]
#except:
#	jid = None

instance = ArgumentParser(description=__doc__)
instance.add_argument("-f", "--file", nargs="*", help="accounting file(s) in .gz")
instance.add_argument("-o", "--owner", nargs="*", help="job owner(s)")
instance.add_argument("-v", "--view", nargs="*", help="SQL views(s)")
args = instance.parse_args()


if (not path.isfile("aws.db")):
	print ("CREATING DATABASE: aws.db")
else:
	remove ("aws.db")
	print ("REPLACING DATABASE: aws.db")


db = connect("aws.db")
db.execute('''CREATE TABLE accounting(
	qname			TEXT		NOT NULL,
	hostname		TEXT		NOT NULL,
	owner			TEXT		NOT NULL,
	job_name		TEXT		NOT NULL,
	job_number		INTEGER		NOT NULL,
	submission_time		INTEGER		NOT NULL,
	start_time		INTEGER		NOT NULL,
	end_time		INTEGER		NOT NULL,
	failed			INTEGER		NOT NULL,
	exit_status		INTEGER		NOT NULL,
	ru_wallclock		INTEGER		NOT NULL,
	io			INTEGER		NOT NULL,
	category		INTEGER		NOT NULL,
	maxvmem			INTEGER		NOT NULL,
	h_rt			INTEGER		NOT NULL,
	h_vmem			INTEGER		NOT NULL,
	mem_free		INTEGER		NOT NULL,
	openmp			INTEGER		NOT NULL	
);''')
db.close()


if args.file:
	for acct in args.file:
		print (acct[-3:])
		with open(acct) as fh:
			for line in fh:
				l = line.decode().rstrip().split(':')
				if l[0].startswith('#'):
					continue
				if args.owner:
					owner_found = 0;
					for owner in args.owner:
						if l[3] == owner:
							owner_found += 1
				if owner_found == 0:
					continue

				a = ''
				for f in FIELDS:
					a = (a + ", '" + f + "'")

				b = ''
				for j in [l[0], l[1], l[3], l[4], l[5], l[8], l[9], l[10], l[11], l[12], l[13], l[21], l[22], l[25]]:
					b = (b + ", '" + j + "'")

				c = ''
				for k in [l[39].split(" ")[7].split(",")[0][5:].replace("G", ""), l[39].split(" ")[7].split(",")[1][7:].replace("G", ""), l[39].split(" ")[7].split(",")[2][9:].replace("G", ""), l[39].split(" ")[10]]:
					c = (c + ", '" + k + "'")

				db = connect("aws.db")
				db.execute("INSERT INTO accounting (" + a[2:] + ") VALUES (" + b[2:] + c + ");")
				db.commit()
				db.close()

	#		d = OrderedDict(zip(FIELDS, l))

	#		if jid:
	#			if d['job_number'] == jid:
	#				for k, v in d.items():
	#					print (k, v)
