#!/usr/bin/python
# -*- coding: utf-8 -*- 
# @File Name: __init__.py
# @Created:   2017-05-21 12:30:29  seo (simon.seo@nyu.edu) 
# @Updated:   2017-05-21 13:41:42  Simon Seo (simon.seo@nyu.edu)

import json
import os.path
import argparse
import multiprocessing as mp
import csv
from time import time
from collections import deque
from util import file_to_list
from crawler import crawl
import pathlib
try:
	from instagram_private_api import (
		Client, __version__ as client_version)
except ImportError:
	import sys
	sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
	from instagram_private_api import (
		Client, __version__ as client_version)


if __name__ == '__main__':
	# Example command:
	# python examples/savesettings_logincallback.py -u "yyy" -p "zzz" -target "names.txt"
	parser = argparse.ArgumentParser(description='Crawling')
	parser.add_argument('-u', '--username', dest='username', type=str, required=True)
	parser.add_argument('-p', '--password', dest='password', type=str, required=True)
	parser.add_argument('-f', '--targetfile', dest='targetfile', type=str, required=False)
	parser.add_argument('-t', '--target', dest='target', type=str, required=False)

	args = parser.parse_args()
	config = {
		'search_algorithm' : 'BFS',               # Possible values: BFS, DFS
		'profile_path' : './hashtags',              # Path where output data gets saved
		'min_collect_media' : 1,                # how many media items to be collected per person/hashtag. If time is specified, this is ignored
		'max_collect_media' : 100,                # how many media items to be collected per person/hashtag. If time is specified, this is ignored
		# 'min_timestamp' : int(time() - 60*60*24*30*2)         # up to how recent you want the posts to be in seconds. If you do not want to use this, put None as value
		'min_timestamp' : None
	}

	try:
		if args.target:
			origin_names = [args.target]
		elif args.targetfile:
			origin_names = file_to_list(args.targetfile)
		else:
			raise Exception('No crawl target given. Provide a hashtag with -t option or file of hashtags with -f')
		print('Client version: %s' % client_version)
		print(origin_names)
		api = Client(args.username, args.password)
	except Exception as e:
		raise Exception("Unable to initiate API:", e)
	else:
		print("Initiating API")

	try:
		# jobs = []
		pathlib.Path(config['profile_path']).mkdir(parents=True, exist_ok=True) 
		for origin in origin_names:
			crawl(api, origin, config)
			# p = mp.Process(target=crawl, args=(api, origin, config))
			# jobs.append(p)
			# p.start()
	except KeyboardInterrupt:
		print('Jobs terminated')
	except Exception as e:
		raise e
	# for p in jobs:
	# 	p.join()

