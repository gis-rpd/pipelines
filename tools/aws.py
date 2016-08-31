#!/usr/bin/env python3
"""
[1]	To create a new database, please specify one or more input accounting filename(s) with -a, and one output database filename with -b. 
[2]	To display a database view, please specify one database filename with -b, one database view with -v, and one or more column widths with -w. 
[3]	To display cluster limits, please specify one database filename with -b, and one or more completed run directories with -c. 
"""

from argparse import ArgumentParser
from collections import OrderedDict
import gzip
from os import listdir, path, remove
from re import findall
from sqlite3 import connect
from sys import argv

def parse_list(l, args, FIELDS):
	if l[0].startswith("#"):
		return ""

	owner_count = 0
	if args.owner:
		for owner in args.owner:
			if l[3] == owner:
				owner_count += 1
	if owner_count == 0:
		return ""

	a = ""
	for f in FIELDS:
		a = (a + ", '" + f + "'")

	b = ""
	for j in [l[0], l[1], l[3], l[4], l[5], l[8], l[9], l[10], l[11], l[12], l[13], l[42]]:
		b = (b + ", '" + j + "'")

	c = ""
	if len(findall("h_rt=\d+", l[39])) > 0:
		c = (c + ", '" + findall("h_rt=\d+", l[39])[0][5:] + "'")
	else:
		c = (c + ", ''")

	if len(findall("h_vmem=\d+", l[39])) > 0:
		c = (c + ", '" + findall("h_vmem=\d+", l[39])[0][7:] + "'")
	else:
		c = (c + ", ''")

	if len(findall("mem_free=\d+", l[39])) > 0:
		c = (c + ", '" + findall("mem_free=\d+", l[39])[0][9:] + "'")
	else:
		c = (c + ", ''")

	if len(findall("OpenMP\s\d+", l[39])) > 0:
		c = (c + ", '" + findall("OpenMP\s\d+", l[39])[0].split(" ")[1] + "'")
	else:
		c = (c + ", ''")

	return "INSERT INTO accounting (" + a[2:] + ") VALUES (" + b[2:] + c + ");"

FIELDS = ['qname', 'hostname', 'owner', 'jobname', 'jobnumber', 'qsub_time', 'start_time', 'end_time', 
          'failed', 'exit_status', 'ru_wallclock', 'maxvmem', 'h_rt', 'h_vmem', 'mem_free', 'slots']

instance = ArgumentParser(description=__doc__)
instance.add_argument("-a", "--accounting", nargs="*", help="accounting filename(s)")
instance.add_argument("-b", "--database", help="database filename")
instance.add_argument("-c", "--completedrun", nargs="*", help="completed run directories")
instance.add_argument("-o", "--owner", nargs="*", help="job owner(s)")
instance.add_argument("-v", "--view", help="database view")
instance.add_argument("-w", "--width", nargs="*", help="column widths")
args = instance.parse_args()

if args.accounting and args.database:
	if (not path.isfile(args.database)):
		print ("CREATING DATABASE:\t" + args.database)
	else:
		remove (args.database)
		print ("REPLACING DATABASE:\t" + args.database)

	db = connect(args.database)
	db.execute('''CREATE TABLE accounting(
	qname			TEXT		NOT NULL,
	hostname		TEXT		NOT NULL,
	owner			TEXT		NOT NULL,
	jobname			TEXT		NOT NULL,
	jobnumber		INTEGER		NOT NULL,
	qsub_time		INTEGER		NOT NULL,
	start_time		INTEGER		NOT NULL,
	end_time		INTEGER		NOT NULL,
	failed			INTEGER		NOT NULL,
	exit_status		INTEGER		NOT NULL,
	ru_wallclock		INTEGER		NOT NULL,
	maxvmem			INTEGER		NOT NULL,
	h_rt			INTEGER,
	h_vmem			INTEGER,
	mem_free		INTEGER,
	slots			INTEGER);''')
	db.close()

	acct_count = 0
	for acct in args.accounting:
		acct_count += 1
		print ("ACCOUNTING FILE (" + str(acct_count) + "/" + str(len(args.accounting)) + "):\t" + acct)
		db = connect(args.database)
		if acct[-3:] == ".gz":
			with gzip.open(acct) as fh:
				for line in fh:
					l = line.decode().rstrip().split(":")
#					db = connect(args.database)
					db.execute(parse_list(l, args, FIELDS))
#					db.commit()
#					db.close()
				fh.close()
		else:
			with open(acct) as fh:
				for line in fh:
					l = line.split(":")
#					db = connect(args.database)
					db.execute(parse_list(l, args, FIELDS))
#					db.commit()
#					db.close()
				fh.close()
		db.commit()
		db.close()

	db = connect(args.database)
	db.execute("CREATE VIEW duplicate_jobs AS SELECT jobnumber, COUNT(*) FROM accounting GROUP BY jobnumber HAVING COUNT(*) > 1;")
	db.execute("CREATE VIEW master_slave_jobs AS SELECT * FROM accounting WHERE (jobname LIKE '%master%') OR (jobname LIKE '%slave%');")
	db.execute("CREATE VIEW success_jobs AS SELECT * FROM accounting WHERE failed = 0 AND exit_status = 0;")
	db.commit()
	db.close()

elif args.database and args.view and args.width:
	db = connect(args.database)

	if args.view == "duplicate_jobs" and len(args.width) == 2:
		print ("jobnumber".ljust(int(args.width[0])) + " " + "COUNT(*)".ljust(int(args.width[1])))
		print ("".ljust(int(args.width[0]), "-") + " " + "".ljust(int(args.width[1]), "-"))
		for record in db.execute("SELECT * FROM duplicate_jobs;"):
			print (str(record[0]).ljust(int(args.width[0])) + " " + str(record[1]).ljust(int(args.width[1])))

	db.commit()
	db.close()

elif args.database and args.completedrun:
	db = connect(args.database)
	for directory in args.completedrun:
		print ((directory + "/logs/").replace("//", "/"))
		for logfile in listdir(directory + "/logs/"):
			if logfile.split(".")[-1][1:].isnumeric():
				print (logfile.split(".")[-1][1:])
	db.commit()
	db.close()
else:
	print (__doc__)
