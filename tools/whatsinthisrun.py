#!/usr/bin/env python3

import sys
import requests

# make sure exactly one arg given
if len(sys.argv) != 2:
	sys.exit("Must give only one run id")

run_num = sys.argv[1]
run_url = 'http://plap18v:8080/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
print(run_url)
r = requests.get(run_url)
#r = requests.post(run_url, data = {"key":"value"})
#r.status_code == requests.codes.ok
if r.status_code != requests.codes.ok:
	r.raise_for_status()

get_data = r.json()
# if runId missing assume wrong run number
if not get_data:
	sys.exit("Run number NOT found in elm: check your runId")

run_id = get_data['runId']
print(run_id)
#with open('config_library.txt', 'w') as fh_out:
for rows in get_data['lanes']:	

	if "MUX" in rows['libraryId']:
		for child in rows['Children']:
			#sample = get_data['runId'] + '\t' + rows['laneId'] + '\t' + rows['libraryId'] + '\tNA\t' + child['barcode'] + '\t' + child['genome'] + '\t' + child['libraryId'] + '\t' + child['libtech'] + '\t' + child['Analysis']
			#print(sample)
			sample1 = (get_data['runId'],rows['laneId'],rows['libraryId'],'\tNA',child['barcode'],child['genome'],child['libraryId'],child['libtech'],child['Analysis'])
			print('\t'.join(sample1))
			    #fh_out.write(sample + '\n')
	else:
		#sample = run_num + '\t' + rows['laneId'] + '\t' + rows['libraryId'] + '\t' + rows['genome'] + '\t' + rows['libtech'] + '\t' + rows['Analysis']
		#print(sample)
		sample1 = (run_num,rows['laneId'],rows['libraryId'],rows['genome'],rows['libtech'],rows['Analysis'])
		print('\t'.join(sample1))
		    #fh_out.write(sample + '\n')