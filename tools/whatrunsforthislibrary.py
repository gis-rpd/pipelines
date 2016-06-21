#!/usr/bin/env python3

import sys
import requests
#import re

if len(sys.argv) != 2:
	sys.exit("Must give only one library id")

library_Id = sys.argv[1]
run_url = 'http://plap18v:8080/rest/libinfo/' + library_Id + '/solexaRun/json'
r = requests.get(run_url)
if r.status_code != requests.codes.ok:
	r.raise_for_status()

get_data = r.json()
#print (type(get_data))
if not get_data:
	sys.exit("Library id NOT found in elm: check your library id")

run_id = get_data['libraryId']
print(run_id)

for rows in get_data['runs']:	

	if "MUX" in get_data['libraryId']:
		for child in rows['lanes']:
			sample = (rows['runId'],child['laneId'],get_data['libraryId'],'\tNA',get_data['multiplexKit'])
			print('\t'.join(sample))
			#sample = rows['runId'] + '\t' + child['laneId'] + '\t' + get_data['libraryId'] + '\tNA\t' + get_data['multiplexKit']
			#print(sample)

	else:
		#MUX = re.search(r'MUX....', get_data['FoundInMux'])
		#if MUX:
	    for child in rows['lanes']:
	    	sample = (rows['runId'],child['laneId'],get_data['libraryId'],child['genome'],get_data['type'],get_data['organism'],get_data['tissueType'],get_data['sample_location'],get_data['target'],get_data['antibody'],get_data['control'],get_data['description'])
	    	print('\t'.join(sample))
	    	#sample = rows['runId'] + '\t' + child['laneId'] + '\t' + get_data['libraryId'] + '\t' + child['genome'] + '\t' + get_data['type'] + '\t' + get_data['organism'] + '\t' + get_data['tissueType'] 
	    	#sample = rows['runId'] + '\t' + child['laneId'] + '\t' + get_data['libraryId'] + '\t' + child['genome'] + '\t' + get_data['type'] + '\t' + get_data['organism'] + '\t' + get_data['tissueType'] + '\t' + get_data['sample_location'] + '\t' + get_data['target'] + '\t' + get_data['antibody'] + '\t' + get_data['control'] + '\t' + get_data['description'] 
	    	#print(sample)