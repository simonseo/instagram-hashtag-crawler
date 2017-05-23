from random import sample, shuffle
import csv

def randselect(list, num):
	l = len(list)
	if l <= num:
		return shuffle(list)
	if l > 5*num: 
		return sample(list[:5*num], num)

def byteify(input):
	if isinstance(input, dict):
		return {byteify(key): byteify(value)
				for key, value in input.iteritems()}
	elif isinstance(input, list):
		return [byteify(element) for element in input]
	elif isinstance(input, unicode):
		return input.encode('utf-8')
	else:
		return input

def file_to_list(file):
	'''1 Dimensional'''
	data = []
	f = open(file, 'r')
	contents = csv.reader(f.read().splitlines())
	count = 0
	try:
		for c in contents:
			count += 1
			data.append(c)
	except Exception as e:
		print("count",count)
		raise e

	if len(data) >= 2:
		return [d[0] for d in data]
	elif len(data) == 1:
		return data[0]
	else:
		return data
	
