#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Precompute and store interesting RXCUI relationships
#
#	2012-09-28	Created by Josh Mandel
#	2014-02-10	Stolen by Pascal Pfiffner
#
#	For profiling: pycallgraph graphviz -- rxnorm-link.py

import sys
import signal
import logging
import couchbase
from datetime import datetime

from rxnorm import RxNorm, RxNormLookup


rxhandle = None

def doQ(q, p):
	return [x[0] for x in rxhandle.fetchAll(q, p)]

def toBrandAndGeneric(rxcuis, tty):
	ret = set()
	for rxcui in rxcuis:
		ret.update(doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela='tradename_of'", (rxcui,)))
	return ret

def toComponents(rxcuis, tty):
	ret = set()

	if tty not in ("SBD", "SCD"):
		return ret

	for rxcui in rxcuis:
		cs = doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela='consists_of'", (rxcui,))
		for c in cs:
			ret.update(doQ("SELECT rxcui from rxnconso where rxcui=? and sab='RXNORM' and tty='SCDC'", (c,)))        

	return ret

def toTreatmentIntents(rxcuis, tty):
	ret = set()
	for rxcui in rxcuis:
		ret.update(toTreatmentIntents_helper(rxcui, tty))
	return ret

def toTreatmentIntents_helper(rxcui, tty):
	assert tty=='IN'
	ret = []
	rxauis = doQ("SELECT rxaui from rxnconso where rxcui=? and tty='FN' and sab='NDFRT'", (rxcui,))
	for a in rxauis:
		a1 = doQ("SELECT rxaui1 from rxnrel where rxaui2=? and rela='may_treat'", (a,))
		if len(a1) > 0:
			dz = doQ("SELECT str from rxnconso where rxaui=? and tty='FN' and sab='NDFRT'", (a1[0],))
			dz = map(lambda x: x.replace(" [Disease/Finding]", ""), dz)
			ret.extend(dz)
	return ret

def toMechanism(rxcuis, tty):
	ret = set()
	for v in rxcuis:
		ret.update(toMechanism_helper(v, tty))
	return ret

def toMechanism_helper(rxcui, tty):
	assert tty=='IN'
	ret = set()
	rxauis = doQ("SELECT rxaui from rxnconso where rxcui=? and tty='FN' and sab='NDFRT'", (rxcui,))
	for a in rxauis:
		a1 = doQ("SELECT rxaui1 from rxnrel where rxaui2=? and rela='has_mechanism_of_action'", (a,))
		if len(a1) > 0:
			moa = doQ("SELECT str from rxnconso where rxaui=? and tty='FN' and sab='NDFRT'", (a1[0],))
			moa = map(lambda x: x.replace(" [MoA]", ""), moa)
			ret.update(moa)
	return ret


def toIngredients(rxcuis, tty):
	ret = set()
	for v in rxcuis:
		ret.update(toIngredients_helper(v, tty))
	return ret

def toIngredients_helper(rxcui, tty):
	if 'IN' == tty:
		return []
	
	# can lookup ingredient directly
	map_direct = {
		'MIN': 'has_part',
		'PIN': 'form_of',
		'BN': 'tradename_of',
		'SCDC': 'has_ingredient',
		'SCDF': 'has_ingredient',
		'SCDG': 'has_ingredient',
	}
	
	if tty in map_direct:
		return doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela=?", (rxcui, map_direct[tty]))
	
	# indirect ingredient lookup
	map_indirect = {
		'BPCK': ('contains', 'SCD'),
		'GPCK': ('contains', 'SCD'),
		'SBD': ('tradename_of', 'SCD'),
		'SBDC': ('tradename_of', 'SCDC'),
		'SBDF': ('tradename_of', 'SCDF'),
		'SBDG': ('tradename_of', 'SCDG'),
		'SCD': ('consists_of', 'SCDC'),
	}
	
	if tty in map_indirect:
		val = map_indirect[tty]
		return toIngredients(doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela=?", (rxcui, val[0])), val[1])
	
	logging.warn('TTY "{}" is not mapped, skipping ingredient lookup'.format(tty))
	return []



if '__main__' == __name__:
	logging.basicConfig(level=logging.INFO)
	
	# install keyboard interrupt handler
	def signal_handler(signal, frame):
		print("\nx>  Aborted")
		sys.exit(0)
	signal.signal(signal.SIGINT, signal_handler)
	
	# prepare databases
	RxNorm.check_database()
	rxhandle = RxNormLookup()
	rxhandle.prepare_to_cache_classes()
	
	# prepare some SQL
	# drug_types = ('SCD', 'SCDC', 'SBDG', 'SBD')
	drug_types = ('SCD', 'SCDC', 'SBDG', 'SBD', 'SBDC', 'BN', 'SBDF', 'SCDG', 'SCDF', 'IN', 'MIN', 'PIN', 'BPCK', 'GPCK')
	param = ', '.join(['?' for x in range(0, len(drug_types))])
	all_sql = "SELECT RXCUI, TTY from RXNCONSO where SAB='RXNORM' and TTY in ({})".format(param)
	label_sql = "SELECT STR from RXNCONSO where RXCUI=? and SAB='RXNORM' and TTY in ({})".format(param)
	
	# prepare Couchbase
	try:
		cb = couchbase.Couchbase.connect(bucket='rxnorm')
	except Exception as e:
		logging.error(e)
		sys.exit(1)
	
	fmt = couchbase.FMT_JSON
	
	# loop all drugs
	all_drugs = rxhandle.fetchAll(all_sql, drug_types)
	num_drugs = len(all_drugs)
	print('->  Indexing {} items'.format(num_drugs))
	
	i = 0
	w_ti = 0
	w_va = 0
	w_either = 0
	last_report = datetime.now()
	for res in all_drugs:
		ingr = toIngredients([res[0]], res[1])
		
		params = [res[0]]
		params.extend(drug_types)
		label = rxhandle.execute(label_sql, params).fetchone()[0]
		
		ti = toTreatmentIntents(ingr, 'IN')
		va = rxhandle.find_va_drug_class(res[0], until_found=True)
		if len(ti) > 0:
			w_ti += 1
		if va is not None:
			w_va += 1
		if va is not None or len(ti) > 0:
			w_either += 1
		
		# create JSON document and insert
		d = {
			'_id': res[0],
			'tty': res[1],
			'label': label,
			'ingredients': list(ingr),
			'generics': list(toBrandAndGeneric([res[0]], res[1])),
			'components': list(toComponents([res[0]], res[1])),
		#   'mechanisms': list(toMechanism(ingr, 'IN')),
			'treatmentIntents': list(ti),
			'va_class': va
		}
		
		# insert into Couchbase (using .set() will overwrite existing documents)
		# print(json.dumps(d, sort_keys=True, indent=2))
		cb.set(res[0], d, format=fmt)
		i += 1
		
		# inform every 5 seconds or so
		if (datetime.now() - last_report).seconds > 5:
			last_report = datetime.now()
			print('->  {:.3%}   n: {}, ti: {}, va: {}, either: {}'.format(i / num_drugs, i, w_ti, w_va, w_either), end="\r")
	
	print('->  {:.3%}   n: {}, ti: {}, va: {}, either: {}'.format(i / num_drugs, i, w_ti, w_va, w_either))
	print('=>  Done')

